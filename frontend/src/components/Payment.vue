<template>
    <div class="bg-white p-6 rounded-lg shadow-md">
      <h3 class="text-lg font-semibold mb-4">Send Blockchain Payment</h3>
      <form @submit.prevent="sendPayment">
        <div class="mb-4">
          <label for="receiver" class="block text-sm font-medium text-gray-700">Receiver Address</label>
          <input
            type="text"
            id="receiver"
            v-model="receiver"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
            placeholder="Enter receiver's blockchain address"
          />
        </div>
        <div class="mb-4">
          <label for="amount" class="block text-sm font-medium text-gray-700">Amount</label>
          <input
            type="number"
            id="amount"
            v-model="amount"
            step="0.01"
            min="0"
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        <button
          type="submit"
          class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          :disabled="!receiver || !amount"
        >
          Send Payment
        </button>
      </form>
      <p v-if="error" class="mt-4 text-red-600">{{ error }}</p>
      <p v-if="success" class="mt-4 text-green-600">{{ success }}</p>
    </div>
  </template>
  
  <script>
  import axios from 'axios'
  
  export default {
    name: 'Payment',
    data() {
      return {
        receiver: '',
        amount: null,
        error: '',
        success: '',
      }
    },
    methods: {
      async sendPayment() {
        this.error = ''
        this.success = ''
        try {
          const response = await axios.post('/blockchain/send_money', {
            sender_address: 'user_address', // Replace with actual sender address
            receiver_address: this.receiver,
            amount: this.amount,
          })
          this.success = `Payment sent successfully: ${response.data.transaction_hash}`
          this.receiver = ''
          this.amount = null
        } catch (error) {
          this.error = `Payment failed: ${error.response?.data?.detail || error.message}`
        }
      },
    },
  }
  </script>
  
  <style scoped>
  </style>