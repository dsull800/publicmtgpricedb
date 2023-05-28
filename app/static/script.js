document.addEventListener("DOMContentLoaded", function() {
  const gifContainers = document.querySelectorAll(".gif-container");

  gifContainers.forEach(function(container) {
    const image = container.querySelector(".gif-image");
    const src = image.getAttribute("src");

    // Preload the GIF
    const img = new Image();
    img.src = src;

    container.addEventListener("mouseenter", function() {
      image.src = src.replace('.png','.gif');
    });

    container.addEventListener("mouseleave", function() {
      image.src = src;
    });
  });

});


