<script setup>
import { onMounted } from 'vue';

onMounted(() => {
  if (typeof KUTE !== 'undefined') {
    KUTE.fromTo(
      "#blob1",
      { path: "#blob1" },
      { path: "#blob2" },
      { repeat: 999, duration: 3000, yoyo: true }
    ).start();
  } else {
    console.error("KUTE.js is not loaded.");
  }
});
</script>

<template>
    <div class="bg-[#282828] text-[#E4FD75] ">
        <section class=" relative min-h-[70vh] overflow-hidden px-4 md:px-12 flex items-center justify-center text-[#E4FD75] rouned-lg">
    <div class="absolute inset-0 w-full h-full z-0">
      <svg id="visual" viewBox="0 0 900 600" xmlns="http://www.w3.org/2000/svg" class="w-full h-full object-cover">
        <g transform="translate(471.96 307.06)">
          <path id="blob1"
            d="M122.5 -133C148.3 -96.6 151.7 -48.3 154 2.4C156.4 53 157.7 106.1 131.9 131.1C106.1 156.1 53 153 -8.8 161.9C-70.7 170.7 -141.4 191.4 -174.3 166.4C-207.1 141.4 -202 70.7 -189.6 12.5C-177.1 -45.7 -157.1 -91.5 -124.3 -127.8C-91.5 -164.1 -45.7 -191.1 1.3 -192.4C48.3 -193.7 96.6 -169.3 122.5 -133"
            fill="#BB004B"></path>
        </g>
        <g transform="translate(473.11 304.90)" style="visibility:hidden;">
          <path id="blob2"
            d="M127.6 -149.9C155.3 -99.9 160.6 -50 165.2 4.6C169.8 59.2 173.7 118.3 146 162C118.3 205.7 59.2 233.8 0.2 233.6C-58.7 233.4 -117.4 204.7 -158.5 161C-199.7 117.4 -223.4 58.7 -211.7 11.7C-200 -35.4 -153 -70.7 -111.9 -120.7C-70.7 -170.7 -35.4 -235.4 7.3 -242.7C50 -250 99.9 -199.9 127.6 -149.9"
            fill="#BB004B"></path>
        </g>
      </svg>
    </div>

    <div class="relative z-10 text-center">
      <h1 class="text-3xl sm:text-4xl md:text-6xl lg:text-8xl mb-4">Shuttle 4 Space</h1>
      <p class="text-sm sm:text-base md:text-lg lg:text-xl">Redefining File Storage, One Node at a Time.</p>
    </div>
  </section>
  <section class="px-4 md:px-12 py-12 md:py-24">
            <h1 class="text-xl sm:text-2xl md:text-8xl mb-4">Hello there!</h1>
            <p class="ltext-xl sm:text-base md:text-xl max-w-4xl">
                Embark on a journey to redefine file storage. With our distributed, peer-to-peer system, your data stays secure, accessible, and completely decentralized.
                <br class="hidden md:block">
                Say goodbye to traditional storage limitations and hello to infinite possibilities in the digital galaxy!
            </p>
        </section>
    </div>
  
</template>
