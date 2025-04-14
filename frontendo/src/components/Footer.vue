<script setup>
    import logod from '@/assets/logod.png';
</script>

<template>
    <div class="bg-[#282828]">
        <footer class="pt-8 md:pt-12 bg-[#282828]">
            <div class="px-4 md:px-8 pt-8 mt-12 text-[#E4FD75]">
                <div class="mx-auto">
                    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                        <!-- Company Info -->
                        <div class="flex items-start space-x-4">
                            <div class="w-20 ">
                                <img :src="logod" class="w-full h-16 rounded-2xl" alt="logo">
                            </div>
                            <div>
                                <h4 class="font-bold text-lg mb-2">Shuttle</h4>
                                <p class="text-gray-500 text-sm">
                                    A1 Street <br> 
                                    Las Vegas USA <br>
                                    9696969696 <br> 
                                    ilios.incorporated@gmail.com
                                </p>
                            </div>
                        </div>

                        <!-- Pages -->
                        <div>
                            <h4 class="font-bold text-lg mb-4">Pages</h4>
                            <ul class="space-y-2">
                                <li><i class="fa fa-chevron-right mr-2"></i><a href="/" class="hover:text-teal-500">Home</a></li>
                                <li><i class="fa fa-chevron-right mr-2"></i><a href="/uploads.html" class="hover:text-teal-500">Uploads</a></li>
                                <li><i class="fa fa-chevron-right mr-2"></i><a href="/about" class="hover:text-teal-500">About</a></li>
                                <li><i class="fa fa-chevron-right mr-2"></i><a href="/bookmarks" class="hover:text-teal-500">Bookmarks</a></li>
                            </ul>
                        </div>

                        <!-- Socials -->
                        <div>
                            <h4 class="font-bold text-lg mb-4">Socials</h4>
                            <ul class="space-y-2">
                                <li><i class="fa-brands fa-square-instagram mr-2"></i> Instagram</li>
                                <li><i class="fa-brands fa-whatsapp mr-2"></i> Whatsapp</li>
                                <li><i class="fa-brands fa-x-twitter mr-2"></i> X</li>
                                <li><i class="fa-brands fa-telegram mr-2"></i> Telegram</li>
                                <li><i class="fa-brands fa-facebook mr-2"></i> Facebook</li>
                                <li><i class="fa-brands fa-linkedin mr-2"></i> LinkedIn</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            <div class="w-full bg-gray-900 text-[#E4FD75] px-4 md:px-10 py-4 mt-8">
                <div class="text-center text-sm">
                    <i class="fa-regular fa-copyright"></i> <span class="font-bold">Shuttle4Space</span>. All rights reserved
                </div>
            </div>
        </footer>
    </div>
    
</template>