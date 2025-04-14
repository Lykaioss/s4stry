<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'vue-toastification';
import FileList from '@/components/FileList.vue';
import CryptoJS from 'crypto-js';

const toast = useToast();
const files = ref([]);
const selectedFile = ref(null);
const fileMeta = ref(null);
const timeDuration = ref(0);
const isRetrieving = ref(false);
const serverUrl = ref(localStorage.getItem('serverUrl') || 'http://localhost:8000');
const showServerConfig = ref(false);
const isUploading = ref(false);

// Encryption/Decryption functions
const encryptFile = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const fileData = e.target.result;
        // Generate a random key
        const key = CryptoJS.lib.WordArray.random(32);
        const iv = CryptoJS.lib.WordArray.random(16);
        
        // Convert the file data to WordArray
        const wordArray = CryptoJS.lib.WordArray.create(fileData);
        
        // Encrypt the file
        const encrypted = CryptoJS.AES.encrypt(wordArray, key, {
          iv: iv,
          mode: CryptoJS.mode.CBC,
          padding: CryptoJS.pad.Pkcs7
        });
        
        // Combine IV and encrypted data
        const result = {
          iv: iv.toString(),
          encryptedData: encrypted.toString(),
          key: key.toString()
        };
        
        resolve(result);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
};

const decryptFile = (encryptedData, key, iv) => {
  try {
    const keyWordArray = CryptoJS.enc.Hex.parse(key);
    const ivWordArray = CryptoJS.enc.Hex.parse(iv);
    
    const decrypted = CryptoJS.AES.decrypt(encryptedData, keyWordArray, {
      iv: ivWordArray,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });
    
    // Convert the decrypted WordArray to a Uint8Array
    const decryptedArray = new Uint8Array(decrypted.sigBytes);
    for (let i = 0; i < decrypted.sigBytes; i++) {
      decryptedArray[i] = (decrypted.words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
    }
    
    return decryptedArray;
  } catch (error) {
    console.error('Decryption error:', error);
    throw error;
  }
};

const updateServerUrl = () => {
  localStorage.setItem('serverUrl', serverUrl.value);
  toast.success('Server URL updated successfully!');
  fetchFiles();
};

const fetchFiles = async () => {
  try {
    const response = await fetch(`${serverUrl.value}/list-files/`);
    const data = await response.json();
    files.value = data.files;
  } catch (error) {
    console.error('Error fetching files:', error);
    toast.error('Failed to fetch uploaded files. Please check server URL.');
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

  isUploading.value = true;
  try {
    // Generate encryption key and IV
    const key = CryptoJS.lib.WordArray.random(32);
    const iv = CryptoJS.lib.WordArray.random(16);
    
    // Read the file and encrypt it
    const reader = new FileReader();
    const fileData = await new Promise((resolve, reject) => {
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsArrayBuffer(selectedFile.value);
    });
    
    // Convert to WordArray and encrypt
    const wordArray = CryptoJS.lib.WordArray.create(fileData);
    const encrypted = CryptoJS.AES.encrypt(wordArray, key, {
      iv: iv,
      mode: CryptoJS.mode.CBC,
      padding: CryptoJS.pad.Pkcs7
    });
    
    // Create a new file with encrypted data
    const encryptedBlob = new Blob([encrypted.toString()], { type: 'text/plain' });
    const encryptedFile = new File([encryptedBlob], selectedFile.value.name, { type: 'text/plain' });
    
    // Create form data
    const formData = new FormData();
    formData.append('file', encryptedFile);
    formData.append('time_duration', timeDuration.value.toString());
    formData.append('encryption_key', key.toString());
    formData.append('iv', iv.toString());

    const response = await fetch(`${serverUrl.value}/upload/`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Upload failed');
    }

    const data = await response.json();
    toast.success(`File "${data.original_name}" uploaded and encrypted successfully!`);
    selectedFile.value = null;
    await fetchFiles();
  } catch (error) {
    console.error('Error uploading file:', error);
    toast.error(`Upload failed: ${error.message}`);
  } finally {
    isUploading.value = false;
  }
};

const handleRetrieve = async (filename) => {
  if (isRetrieving.value) return;
  isRetrieving.value = true;

  try {
    // First get the encryption key and IV
    const keyResponse = await fetch(`${serverUrl.value}/get-key/${filename}`);
    if (!keyResponse.ok) {
      throw new Error('Failed to get encryption key');
    }
    const { encryption_key, iv } = await keyResponse.json();

    // Then get the encrypted file
    const fileResponse = await fetch(`${serverUrl.value}/download/${filename}`);
    if (!fileResponse.ok) {
      throw new Error('Failed to download file');
    }
    
    // Get the encrypted data as text
    const encryptedData = await fileResponse.text();
    
    // Decrypt the file
    const decryptedData = decryptFile(encryptedData, encryption_key, iv);
    
    // Create a blob from the decrypted data
    const blob = new Blob([decryptedData], { type: 'application/octet-stream' });
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    await fetchFiles();
    toast.success(`File "${filename}" retrieved and decrypted successfully! Check your browser's downloads folder.`);
  } catch (error) {
    console.error('Error retrieving file:', error);
    toast.error(`Retrieval failed: ${error.message}`);
  } finally {
    isRetrieving.value = false;
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
      <div class="flex justify-between items-center mb-8">
        <h1 class="text-3xl font-bold text-white">Distributed Storage System</h1>
        <button
          @click="showServerConfig = !showServerConfig"
          class="bg-[#E4FD75] text-[#282828] px-4 py-2 rounded hover:bg-[#d4ed65] transition-colors"
        >
          {{ showServerConfig ? 'Hide Server Config' : 'Server Config' }}
        </button>
      </div>

      <!-- Server Configuration -->
      <div v-if="showServerConfig" class="bg-[#E4FD75] rounded-lg shadow p-6 mb-8">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">Server Configuration</h2>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Server URL</label>
            <input
              type="text"
              v-model="serverUrl"
              placeholder="http://localhost:8000"
              class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
          <button
            @click="updateServerUrl"
            class="w-full bg-[#282828] text-[#E4FD75] py-2 px-4 rounded hover:bg-gray-800 transition-colors"
          >
            Update Server URL
          </button>
        </div>
      </div>
      
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
                file:bg-[#282828] file:text-[#E4FD75]
                hover:file:bg-gray-800"
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
            class="w-full bg-[#282828] text-[#E4FD75] py-2 px-4 rounded hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
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
