<script setup>
    import {ref} from 'vue';

    const isSignUp = ref(false);

    const toggleForm = () =>{
        isSignUp.value = !isSignUp.value;
    };

</script>

<template>
    <div class="flex items-center justify-center min-h-screen bg-boom px-4">
    <div class="w-full max-w-md bg-gray-700 p-6 rounded-lg shadow-lg">
      <h2 class="text-2xl font-semibold text-white text-center">
        {{ isSignUp ? "Sign Up" : "Sign In" }}
      </h2>

      <form class="mt-4 space-y-3">
        <!-- Username Field (Shown Only in Sign Up Mode) -->
        <div v-if="isSignUp">
          <label class="block text-sm font-medium text-[#E4FD75]">Username</label>
          <input
            type="text"
            class="mt-1 p-2 w-full border rounded-md focus:outline-none focus:ring-2 focus:ring-secondary"
            placeholder="Enter your username"
          />
        </div>

        <!-- Email Field -->
        <div>
          <label class="block text-sm font-medium text-[#E4FD75]">Email</label>
          <input
            type="email"
            class="mt-1 p-2 w-full border rounded-md focus:outline-none focus:ring-2 focus:ring-secondary"
            placeholder="Enter your email"
          />
        </div>

        <!-- Password Field -->
        <div>
          <label class="block text-sm font-medium text-[#E4FD75]">Password</label>
          <input
            type="password"
            class="mt-1 p-2 w-full border rounded-md focus:outline-none focus:ring-2 focus:ring-secondary"
            placeholder="Enter your password"
          />
        </div>

        <!-- Submit Button -->
        <button
          class="w-full bg-second text-black p-2 rounded-md hover:bg-red-500 transition duration-300"
        >
          {{ isSignUp ? "Sign Up" : "Sign In" }}
        </button>
      </form>

      <!-- Toggle between Sign In & Sign Up -->
      <p class="text-center text-sm mt-4 text-white">
        {{ isSignUp ? "Already have an account?" : "Don't have an account?" }}
        <button
          class="font-medium text-secondary hover:text-[#E4FD75] transition duration-300"
          @click="toggleForm"
        >
          {{ isSignUp ? "Sign In" : "Sign Up" }}
        </button>
      </p>
    </div>
  </div>
</template>


<style scoped>
/* Custom Tailwind theme colors */
.bg-boom {
  background-color: #001220;
}

.bg-secondary {
  background-color: #e34c67;
}
.bg-second {
  background-color: #E4FD75;
}


</style>