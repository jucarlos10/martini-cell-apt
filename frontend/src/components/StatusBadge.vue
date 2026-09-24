<script setup>
const props=defineProps({status:String,label:String})
const tone={RECEIVED:'secondary',DIAGNOSIS:'info',AUTHORIZATION:'warning',PART:'warning',REPAIR:'primary',TESTING:'info',READY:'success',DELIVERED:'success',CLOSED:'dark',REJECTED:'danger'}
</script>
<template><span class="badge rounded-pill" :class="`text-bg-${tone[props.status]||'primary'}`">{{label}}</span></template>
