document.addEventListener("DOMContentLoaded", () => {
  if (window.AOS) {
    AOS.init({ duration: 650, once: true, offset: 40 });
  }

  if (window.Fancybox) {
    Fancybox.bind("[data-fancybox]", {});
  }

  const el = document.querySelector(".swiper");
  if (el && window.Swiper) {
    new Swiper(".swiper", {
      loop: true,
      slidesPerView: 1,
      spaceBetween: 16,
      autoplay: { delay: 3500, disableOnInteraction: false },
      breakpoints: {
        768: { slidesPerView: 2 },
        992: { slidesPerView: 3 },
      },
    });
  }
});
