<template>
  <div class="space-y-4">
    <div v-for="file in files" :key="file.filename" class="bg-white rounded-lg shadow p-4">
      <div class="flex flex-col space-y-2">
        <div class="flex flex-col">
          <span class="text-lg font-semibold text-gray-800">{{ file.original_name }}</span>
          <span class="text-sm text-gray-500">Uploaded: {{ formatDate(file.upload_time) }}</span>
          <span v-if="file.time_duration > 0" class="text-sm text-blue-600">
            Auto-retrieve after: {{ file.time_duration }} minutes
          </span>
        </div>
        
        <div class="flex space-x-2">
          <button
            @click="retrieveFile(file.filename)"
            :disabled="file.is_retrieved"
            :class="[
              'px-4 py-2 rounded',
              file.is_retrieved
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            ]"
          >
            {{ file.is_retrieved ? 'Retrieved' : 'Retrieve' }}
          </button>
          
          <button
            @click="deleteFile(file.filename)"
            class="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

const props = defineProps({
  files: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['retrieve', 'delete'])

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const retrieveFile = (filename) => {
  emit('retrieve', filename)
}

const deleteFile = (filename) => {
  emit('delete', filename)
}
</script> 