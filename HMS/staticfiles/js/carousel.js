document.addEventListener('DOMContentLoaded', () => {
  const track = document.querySelector('.carousel-track');
  const images = Array.from(track.children);
  const nextButton = document.querySelector('.next');
  const prevButton = document.querySelector('.prev');

  let index = 0;
  const imageWidth = 400;
  const intervalTime = 3000; // 3 seconds

  function updateCarousel() {
    track.style.transform = `translateX(-${index * imageWidth}px)`;
  }

  function showNextImage() {
    index = (index + 1) % images.length;
    updateCarousel();
  }

  nextButton.addEventListener('click', () => {
    showNextImage();
    resetAutoplay(); // Pause and restart autoplay on manual navigation
  });

  prevButton.addEventListener('click', () => {
    index = (index -1 + images.length) % images.length;
    updateCarousel();
    resetAutoplay();
  });

  // Auto-slide logic
  let autoplay = setInterval(showNextImage, intervalTime);

  function resetAutoplay() {
    clearInterval(autoplay);
    autoplay = setInterval(showNextImage, intervalTime);
  }
});
