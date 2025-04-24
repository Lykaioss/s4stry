<template>
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-lg font-semibold mb-4">Retrieve File</h3>
      <form @submit.prevent="retrieveFile">
        <div class="mb-4">
          <label for="filename" class="block text-sm font-medium text-gray-700">File Name</label>
          <input
            type="text"
            id="filename"
            v-model="filename"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            placeholder="Enter file name"
          />
        </div>
        <div class="mb-4">
          <label for="destination" class="block text-sm font-medium text-gray-700">Destination Path (optional)</label>
          <input
            type="text"
            id="destination"
            v-model="destination"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            placeholder="Leave blank for default downloads"
          />
        </div>
        <button
          type="submit"
          class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          :disabled="!filename"
        >
          Retrieve
        </button>
      </form>
      <p v-if="error" class="mt-4 text-red-600">{{ error }}</p>
      <p v-if="success" class="mt-4 text-green-600">{{ success }}</p>
    </div>
  </template>
  
  <script>
  import axios from 'axios'
  
  export default {
    name: 'FileRetrieve',
    data() {
      return {
        filename: '',
        destination: '',
        error: '',
        success: '',
      }
    },
    methods: {
      async retrieveFile() {
        this.error = ''
        this.success = ''
        try {
          const response = await axios.get(`/api/download/${this.filename}`, {
            params: { username: 'user' }, // Replace with actual username
          })
          // Assume challenge-response is handled server-side
          const blob = new Blob([response.data])
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = this.filename
          a.click()
          window.URL.revokeObjectURL(url)
          this.success = `File ${this.filename} retrieved successfully`
          this.filename = ''
          this.destination = ''
        } catch (error) {
          this.error = `Retrieval failed: ${error.response?.data?.detail || error.message}`
        }
      },
    },
  }
  </script>
  
  <style scoped>
  </style>