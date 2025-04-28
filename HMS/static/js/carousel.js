const track = document.querySelector('.carousel-track');
const images = Array.from(track.children);
const nextButton = document.querySelector('.next');
const prevButton = document.querySelector('.prev');

let index = 0;
let isTransitioning = true;

// Clone first and last images for seamless looping
const firstClone = images[0].cloneNode(true);
const lastClone = images[images.length - 1].cloneNode(true);
track.appendChild(firstClone);
track.insertBefore(lastClone, images[0]);

// Update the track's position to account for the prepended clone
track.style.transform = `translateX(-400px)`;

// Update carousel function
function updateCarousel() {
  track.style.transition = 'transform 0.5s ease-in-out';
  track.style.transform = `translateX(-${(index + 1) * 400}px)`;
}

// Handle transition end for seamless looping
track.addEventListener('transitionend', () => {
  if (index === images.length) {
    index = 0;
    track.style.transition = 'none';
    track.style.transform = `translateX(-400px)`;
  } else if (index === -1) {
    index = images.length - 1;
    track.style.transition = 'none';
    track.style.transform = `translateX(-${images.length * 400}px)`;
  }
  isTransitioning = false;
});

// Next button functionality
nextButton.addEventListener('click', () => {
  if (isTransitioning) return;
  isTransitioning = true;
  index++;
  updateCarousel();
});

// Previous button functionality
prevButton.addEventListener('click', () => {
  if (isTransitioning) return;
  isTransitioning = true;
  index--;
  updateCarousel();
});

// Automate movement of images
setInterval(() => {
  if (!isTransitioning) {
    isTransitioning = true;
    index++;
    updateCarousel();
  }
}, 3000); // Change image every 3 seconds