<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'vue-toastification';
import FileList from '@/components/FileList.vue';

const toast = useToast();
const files = ref([]);
const selectedFile = ref(null);
const fileMeta = ref(null);
const timeDuration = ref(0);
const isRetrieving = ref(false);

const fetchFiles = async () => {
  try {
    const response = await fetch('http://localhost:8000/list-files/');
    const data = await response.json();
    files.value = data.files;
  } catch (error) {
    console.error('Error fetching files:', error);
    toast.error('Failed to fetch uploaded files');
  }
};

const handleFileChange = (e) => {
  selectedFile.value = e.target.files[0];
};

const uploadFile = async () => {
  if (!selectedFile.value) {
    toast.error('Please select a file to upload');
    return;
  }

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('time_duration', timeDuration.value);

  try {
    const response = await fetch('http://localhost:8000/upload/', {
      method: 'POST',
      body: formData
    });

    if (response.ok) {
      await fetchFiles();
      toast.success(`File "${selectedFile.value.name}" uploaded successfully!`);
      selectedFile.value = null;
      timeDuration.value = 0;
    } else {
      const errorData = await response.json();
      toast.error(`Upload failed: ${errorData.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error uploading file:', error);
    toast.error(`Upload failed: ${error.message}`);
  }
};

const handleRetrieve = async (filename) => {
  if (isRetrieving.value) return;
  isRetrieving.value = true;

  try {
    const response = await fetch(`http://localhost:8000/download/${filename}`);
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      await fetchFiles();
      toast.success(`File "${filename}" retrieved successfully!`);
    } else {
      const errorData = await response.json();
      toast.error(`Retrieval failed: ${errorData.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error retrieving file:', error);
    toast.error(`Retrieval failed: ${error.message}`);
  } finally {
    isRetrieving.value = false;
  }
};

const handleDelete = async (filename) => {
  try {
    const response = await fetch(`http://localhost:8000/delete/${filename}`, {
      method: 'POST'
    });
    if (response.ok) {
      await fetchFiles();
      toast.success(`File "${filename}" deleted successfully!`);
    } else {
      const errorData = await response.json();
      toast.error(`Deletion failed: ${errorData.detail || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting file:', error);
    toast.error(`Deletion failed: ${error.message}`);
  }
};

onMounted(() => {
  fetchFiles();
  setInterval(fetchFiles, 5000);
});
</script>

<template>
  <div class="min-h-screen bg-[#282828] py-8">
    <div class="max-w-4xl mx-auto px-4">
      <h1 class="text-3xl font-bold text-gray-800 mb-8">Distributed Storage System</h1>
      
      <!-- File Upload Section -->
      <div class="bg-[#E4FD75] rounded-lg shadow p-6 mb-8">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">Upload File</h2>
        <form @submit.prevent="uploadFile" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">File</label>
            <input
              type="file"
              @change="handleFileChange"
              class="block w-full text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-full file:border-0
                file:text-sm file:font-semibold
                file:bg-[#282828] file:text-blue-700
                hover:file:bg-blue-100"
            />
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Auto-retrieve after (minutes)</label>
            <input
              type="number"
              v-model="timeDuration"
              min="0"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          
          <button
            type="submit"
            :disabled="!selectedFile"
            class="w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Upload
          </button>
        </form>
      </div>
      
      <!-- File List Section -->
      <div class="bg-[#E4FD75] rounded-lg shadow p-6">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">Uploaded Files</h2>
        <FileList
          :files="files"
          @retrieve="handleRetrieve"
          @delete="handleDelete"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.bg-secondary {
  background-color: #e34c67;
}
</style>
