<template>
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-lg font-semibold mb-4">Upload File</h3>
      <form @submit.prevent="uploadFile">
        <div class="mb-4">
          <input
            type="file"
            ref="fileInput"
            @change="onFileChange"
            class="block w-full text-sm text-gray-500
                   file:mr-4 file:py-2 file:px-4
                   file:rounded-full file:border-0
                   file:text-sm file:font-semibold
                   file:bg-blue-50 file:text-blue-700
                   hover:file:bg-blue-100"
          />
        </div>
        <div class="mb-4">
          <label for="duration" class="block text-sm font-medium text-gray-700">Auto-retrieval Duration (minutes)</label>
          <input
            type="number"
            id="duration"
            v-model="duration"
            min="1"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        <div v-if="cost" class="mb-4 text-green-600">
          Estimated Cost: ${{ cost.toFixed(2) }}
        </div>
        <button
          type="submit"
          class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          :disabled="!file || !cost"
        >
          Upload
        </button>
      </form>
      <p v-if="error" class="mt-4 text-red-600">{{ error }}</p>
      <p v-if="success" class="mt-4 text-green-600">{{ success }}</p>
    </div>
  </template>
  
  <script>
  import axios from 'axios'
  
  export default {
    name: 'FileUpload',
    data() {
      return {
        file: null,
        duration: 1,
        cost: null,
        error: '',
        success: '',
      }
    },
    methods: {
      onFileChange(event) {
        this.file = event.target.files[0]
        this.calculateCost()
      },
      async calculateCost() {
        if (!this.file) return
        const fileSizeMB = this.file.size / (1024 * 1024)
        const BASE_COST_PER_MB_PER_MINUTE = 0.01
        this.cost = (fileSizeMB * this.duration * BASE_COST_PER_MB_PER_MINUTE).toFixed(2)
      },
      async uploadFile() {
        this.error = ''
        this.success = ''
        if (!this.file) {
          this.error = 'Please select a file.'
          return
        }
        try {
          const formData = new FormData()
          formData.append('file', this.file)
          const response = await axios.post('/api/upload/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          this.success = `File uploaded successfully: ${response.data.message}`
          this.file = null
          this.$refs.fileInput.value = ''
          this.cost = null
        } catch (error) {
          this.error = `Upload failed: ${error.response?.data?.detail || error.message}`
        }
      },
    },
    watch: {
      duration() {
        this.calculateCost()
      },
    },
  }
  </script>
  
  <style scoped>
  </style>