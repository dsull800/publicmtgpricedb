import psycopg2
import json
import sagemaker
import boto3
import numpy as np
import pandas as pd
import os
from creds.credentials import host, dbname, password, user


def get_namerows():
    conn = psycopg2.connect(host=host, user=user,
                            password=password, database=dbname)

    cur = conn.cursor()

    cur.execute('''SELECT cardname FROM public.model_cardnames ORDER BY cardname ASC''')

    namerows = cur.fetchall()

    return namerows


def create_sage_endpoint(environment):
    namerows = get_namerows()

    if environment.lower() == "local":
        # from sagemaker.local import LocalSession
        # sagemaker_session = LocalSession(boto_session=boto3.session.Session())
        # sagemaker_session.config = {'local': {'local_code': True}}
        class predictor:
            def __init__(self, **kwargs):
                pass

            def predict(self, **kwargs):
                return pd.DataFrame([[1, 2, 3]], columns=['0.05', '0.5', '0.85'], index=['2021-10-05'])

        return namerows, predictor()

    elif environment.lower() == "production":
        sagemaker_session = sagemaker.Session(boto3.session.Session())

    else:
        raise Exception("use a correct ENV file")

    sage_client = boto3.client('sagemaker')

    from sagemaker.serializers import IdentitySerializer
    class DeepARPredictor(sagemaker.predictor.Predictor):

        def __init__(self, *args, **kwargs):
            super().__init__(*args,
                             # serializer=JSONSerializer(),
                             serializer=IdentitySerializer(content_type="application/json"),
                             **kwargs)

        def predict(self, ts, cat=None, dynamic_feat=None,
                    num_samples=100, return_samples=False, quantiles=["0.1", "0.5", "0.9"]):
            """Requests the prediction of for the time series listed in `ts`, each with the (optional)
            corresponding category listed in `cat`.
            
            ts -- `pandas.Series` object, the time series to predict
            cat -- integer, the group associated to the time series (default: None)
            num_samples -- integer, number of samples to compute at prediction time (default: 100)
            return_samples -- boolean indicating whether to include samples in the response (default: False)
            quantiles -- list of strings specifying the quantiles to compute (default: ["0.1", "0.5", "0.9"])
            
            Return value: list of `pandas.DataFrame` objects, each containing the predictions
            """
            prediction_time = ts.index[-1] + ts.index.freq
            quantiles = [str(q) for q in quantiles]
            req = self.__encode_request(ts, cat, dynamic_feat, num_samples, return_samples, quantiles)
            res = super(DeepARPredictor, self).predict(req)
            return self.__decode_response(res, ts.index.freq, prediction_time, return_samples)

        def __encode_request(self, ts, cat, dynamic_feat, num_samples, return_samples, quantiles):
            instance = series_to_dict(ts, cat if cat is not None else None, dynamic_feat if dynamic_feat else None)

            configuration = {
                "num_samples": num_samples,
                "output_types": ["quantiles", "samples"] if return_samples else ["quantiles"],
                "quantiles": quantiles
            }

            http_request_data = {
                "instances": [instance],
                "configuration": configuration
            }

            return json.dumps(http_request_data).encode('utf-8')

        def __decode_response(self, response, freq, prediction_time, return_samples):
            # we only sent one time series so we only receive one in return
            # however, if possible one will pass multiple time series as predictions will then be faster
            predictions = json.loads(response.decode('utf-8'))['predictions'][0]
            prediction_length = len(next(iter(predictions['quantiles'].values())))
            prediction_index = pd.date_range(start=prediction_time, freq=freq, periods=prediction_length)
            if return_samples:
                dict_of_samples = {'sample_' + str(i): s for i, s in enumerate(predictions['samples'])}
            else:
                dict_of_samples = {}
            return pd.DataFrame(data={**predictions['quantiles'], **dict_of_samples}, index=prediction_index)

        def set_frequency(self, freq):
            self.freq = freq

    def encode_target(ts):
        return [x if np.isfinite(x) else "NaN" for x in ts]

    def series_to_dict(ts, cat=None, dynamic_feat=None):
        """Given a pandas.Series object, returns a dictionary encoding the time series.

        ts -- a pands.Series object with the target time series
        cat -- an integer indicating the time series category

        Return value: a dictionary
        """
        obj = {"start": str(ts.index[0]), "target": encode_target(ts)}
        if cat is not None:
            obj["cat"] = cat
        if dynamic_feat is not None:
            obj["dynamic_feat"] = dynamic_feat
        return obj

    available_endpoints = sage_client.list_endpoints()['Endpoints']

    if os.environ['ENDPOINT_NAME'] in [endpoint['EndpointName'] for endpoint in available_endpoints]:
        predictor = DeepARPredictor(endpoint_name=os.environ['ENDPOINT_NAME'],
                                    sagemaker_session=sagemaker_session)

        return namerows, predictor
    try:

        sage_client.delete_endpoint_config(EndpointConfigName=os.environ['ENDPOINT_NAME'])

        training_job_name = sage_client.list_training_jobs()['TrainingJobSummaries'][0]['TrainingJobName']

        attached_estimator = sagemaker.estimator.Estimator.attach(training_job_name, sagemaker_session=sagemaker_session)

        predictor = attached_estimator.deploy(initial_instance_count=1,
                                              instance_type='ml.t2.medium',
                                              predictor_cls=DeepARPredictor,
                                              endpoint_name=os.environ['ENDPOINT_NAME'],
                                              wait=False)
    except Exception as e:
        return namerows, None


    return namerows, predictor
