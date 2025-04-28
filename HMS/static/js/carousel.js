const track = document.querySelector('.carousel-track');
const images = Array.from(track.children);
const nextButton = document.querySelector('.next');
const prevButton = document.querySelector('.prev');

let index = 0;

function updateCarousel() {
  track.style.transform = `translateX(-${index * 400}px)`;
}

nextButton.addEventListener('click', () => {
  index = (index + 1) % images.length;
  updateCarousel();
});

prevButton.addEventListener('click', () => {
  index = (index - 1 + images.length) % images.length;
  updateCarousel();
});
