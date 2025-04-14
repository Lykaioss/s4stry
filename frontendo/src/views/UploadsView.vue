<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'vue-toastification';

const toast = useToast();
const selectedFile = ref(null);
const fileMeta = ref(null);
const timeDuration = ref(0);
const uploadedFiles = ref([]);
const isRetrieving = ref(false);

const handleFileChange = (e) => {
  selectedFile.value = e.target.files[0];
};

const uploadFile = async () => {
  if (!selectedFile.value) {
    toast.error("Please select a file to upload!");
    return;
  }

  // Set file metadata after clicking submit
  fileMeta.value = {
    name: selectedFile.value.name,
    size: (selectedFile.value.size / 1024).toFixed(2) + " KB",
    type: selectedFile.value.type || "Unknown",
  };

  try {
    const formData = new FormData();
    formData.append('file', selectedFile.value);
    formData.append('time_duration', timeDuration.value);

    const response = await fetch('http://localhost:8000/upload/', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    const data = await response.json();
    uploadedFiles.value.push({
      filename: data.filename,
      originalName: data.original_name,
      uploadTime: new Date().toISOString(),
      timeDuration: timeDuration.value
    });
    
    toast.success(`✅ ${selectedFile.value.name} uploaded successfully!`);
    selectedFile.value = null;
    timeDuration.value = 0;
  } catch (error) {
    toast.error(`❌ Upload failed: ${error.message}`);
  }
};

const retrieveFile = async (filename) => {
  if (isRetrieving.value) return;
  
  try {
    isRetrieving.value = true;
    const response = await fetch(`http://localhost:8000/download/${filename}`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error('File retrieval failed');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    toast.success('File retrieved successfully!');
  } catch (error) {
    toast.error(`❌ File retrieval failed: ${error.message}`);
  } finally {
    isRetrieving.value = false;
  }
};

// Fetch uploaded files on component mount
onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8000/list-files/');
    if (response.ok) {
      const data = await response.json();
      uploadedFiles.value = data.files;
    }
  } catch (error) {
    toast.error('Failed to fetch uploaded files');
  }
});
</script>

<template>
  <div class="bg-[#282828] min-h-screen">
    <section
      class="mx-4 md:mx-12 p-6 md:p-10 text-white rounded-lg flex flex-col md:flex-row items-center md:items-start justify-between shadow-lg"
    >
      <div class="w-full md:w-1/2">
        <h1 class="mb-6 text-xl md:text-3xl font-bold text-center md:text-left">
          🚀 Upload your files and send them into orbit!
        </h1>

        <div class="space-y-4">
          <form @submit.prevent="uploadFile" class="flex flex-col space-y-4">
            <label for="file" class="text-lg">Select a File</label>
            <input
              id="file"
              name="file"
              type="file"
              class="w-full text-sm md:text-base bg-white text-black p-2 rounded-md shadow-md"
              @change="handleFileChange"
            />
            
            <div class="flex flex-col space-y-2">
              <label for="timeDuration" class="text-lg">Auto-Retrieve Duration (minutes)</label>
              <input
                id="timeDuration"
                v-model="timeDuration"
                type="number"
                min="0"
                class="w-full text-sm md:text-base bg-white text-black p-2 rounded-md shadow-md"
                placeholder="Enter duration in minutes (0 for no auto-retrieve)"
              />
            </div>

            <button
              type="submit"
              class="bg-secondary px-5 py-3 rounded-md w-full md:w-auto hover:opacity-90 transition-opacity text-white font-semibold text-center"
            >
              Upload File 🚀
            </button>
          </form>
        </div>
      </div>

      <!-- File Metadata Display -->
      <div
        v-if="fileMeta"
        class="mt-6 md:mt-0 w-full md:w-1/3 bg-[#E4FD75] p-4 md:p-6 rounded-md shadow-lg"
      >
        <h2 class="text-lg text-[#282828] font-semibold text-center">File Details</h2>
        <div class="mt-2 text-sm md:text-base text-[#282828]">
          <p><strong>Name:</strong> {{ fileMeta.name }}</p>
          <p><strong>Size:</strong> {{ fileMeta.size }}</p>
          <p><strong>Type:</strong> {{ fileMeta.type }}</p>
        </div>
      </div>
    </section>

    <!-- Uploaded Files List -->
    <section class="mx-4 md:mx-12 mt-8 p-6 bg-white rounded-lg shadow-lg">
      <h2 class="text-2xl font-bold text-[#282828] mb-4">Uploaded Files</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full bg-white">
          <thead>
            <tr>
              <th class="px-6 py-3 border-b-2 border-gray-200 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Original Name</th>
              <th class="px-6 py-3 border-b-2 border-gray-200 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Upload Time</th>
              <th class="px-6 py-3 border-b-2 border-gray-200 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Auto-Retrieve Duration</th>
              <th class="px-6 py-3 border-b-2 border-gray-200 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="file in uploadedFiles" :key="file.filename" class="hover:bg-gray-100">
              <td class="px-6 py-4 border-b border-gray-200">{{ file.originalName }}</td>
              <td class="px-6 py-4 border-b border-gray-200">{{ new Date(file.uploadTime).toLocaleString() }}</td>
              <td class="px-6 py-4 border-b border-gray-200">{{ file.timeDuration }} minutes</td>
              <td class="px-6 py-4 border-b border-gray-200">
                <button
                  @click="retrieveFile(file.filename)"
                  :disabled="isRetrieving"
                  class="bg-secondary text-white px-4 py-2 rounded-md hover:opacity-90 transition-opacity"
                >
                  {{ isRetrieving ? 'Retrieving...' : 'Retrieve' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.bg-secondary {
  background-color: #e34c67;
}
</style>
