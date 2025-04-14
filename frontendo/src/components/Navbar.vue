<script setup>
    import popo from '@/assets/popo.png'
    import { RouterLink , useRoute } from 'vue-router';

    const isActive = (routePath) =>{
        const route = useRoute();
        return route.path === routePath;
    }

</script>

<template>

    <div class="bg-[#282828] p-4">
        <nav class=" bg-[#E4FD75] border-b border-black rounded-lg  ">
        <div class="mx-auto px-2 sm:px-6 lg:px-8">
            <div class="flex h-20 items-center justify-between">
                <div class="flex flex-1 items-center justify-center md:items-stretch md:justify-start">
                    <a class="flex flex-shrink-0 items-center mr-4" href="#">
              <img class="h-10 w-auto rounded-2xl" :src="popo" alt="Vue Jobs" />
              <span class="hidden md:block text-black text-2xl font-bold ml-2"
                >Vue Jobs</span>
                    </a>

                    <div class="md:ml-auto">
                        <div class="flex space-x-2">
                            <RouterLink to="/" 
                            :class="[isActive('/') ? 'bg-[#E4FD75] font-medium !text-black hover:text-black  ':'bg-[#282828] hover:text-white', 'text-white px-3 py-2 rounded-md' ] ">
                                Home
                            </RouterLink>
                            <RouterLink to="/upload"
                            :class="[isActive('/upload') ? 'bg-[#E4FD75] font-medium !text-black hover:text-black  ':'bg-[#282828] hover:text-white', 'text-white px-3 py-2 rounded-md' ] ">
                                Uploads
                            </RouterLink>
                            <a href="#" 
                            class=" bg-[#282828] hover:text-white text-white px-3 py-2 rounded-md">
                                About
                            </a>
                            <a href="#" 
                            class=" bg-[#282828] hover:text-white text-white px-3 py-2 rounded-md">
                                Profile
                            </a>
                            <RouterLink to="/log"
                            :class="[isActive('/log') ? 'bg-[#E4FD75] font-medium !text-black hover:text-black  ':'bg-[#282828] hover:text-white', 'text-white px-3 py-2 rounded-md' ] ">
                                Login
                            </RouterLink>
                            
                        </div>

                    </div>


                </div>
            </div>

        </div>

    </nav>
    </div>

    

</template>