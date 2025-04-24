<template>
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-lg font-semibold mb-4">Check Blockchain Balance</h3>
      <button
        @click="checkBalance"
        class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        Check Balance
      </button>
      <p v-if="balance !== null" class="mt-4 text-green-600">Your balance: {{ balance }}</p>
      <p v-if="error" class="mt-4 text-red-600">{{ error }}</p>
    </div>
  </template>
  
  <script>
  import axios from 'axios'
  
  export default {
    name: 'BalanceCheck',
    data() {
      return {
        balance: null,
        error: '',
      }
    },
    methods: {
      async checkBalance() {
        this.error = ''
        this.balance = null
        try {
          const response = await axios.get('/blockchain/get_balance', {
            params: { address: 'user_address' }, // Replace with actual address
          })
          this.balance = response.data.balance
        } catch (error) {
          this.error = `Failed to check balance: ${error.response?.data?.detail || error.message}`
        }
      },
    },
  }
  </script>
  
  <style scoped>
  </style>