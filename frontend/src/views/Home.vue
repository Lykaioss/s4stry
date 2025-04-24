<template>
  <div class="space-y-8">
    <h2 class="text-xl font-semibold">Welcome to S4Stry</h2>
    <FileUpload />
    <FileRetrieve />
    <BalanceCheck />
    <Payment />
  </div>
</template>

<script>
import FileUpload from '../components/FileUpload.vue'
import FileRetrieve from '../components/FileRetrieve.vue'
import BalanceCheck from '../components/BalanceCheck.vue'
import Payment from '../components/Payment.vue'

export default {
  name: 'Home',
  components: {
    FileUpload,
    FileRetrieve,
    BalanceCheck,
    Payment,
  },
}
</script>

<style scoped>
</style>