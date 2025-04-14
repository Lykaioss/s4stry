<template>
  <div class="space-y-4">
    <div v-if="files.length === 0" class="text-center text-gray-500 py-4">
      No files uploaded yet
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="file in files"
        :key="file.filename"
        class="flex items-center justify-between p-4 bg-white rounded-lg shadow"
      >
        <div class="flex-1">
          <h3 class="text-lg font-medium text-gray-800">{{ file.filename }}</h3>
          <p class="text-sm text-gray-500">
            Size: {{ file.size }} | Uploaded: {{ formatDate(file.upload_time) }}
          </p>
        </div>
        <button
          @click="$emit('retrieve', file.filename)"
          :disabled="file.is_retrieved"
          class="px-4 py-2 rounded text-sm font-medium transition-colors"
          :class="{
            'bg-[#282828] text-[#E4FD75] hover:bg-gray-800': !file.is_retrieved,
            'bg-gray-300 text-gray-500 cursor-not-allowed': file.is_retrieved
          }"
        >
          {{ file.is_retrieved ? 'Retrieved' : 'Retrieve' }}
        </button>
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

const emit = defineEmits(['retrieve'])

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