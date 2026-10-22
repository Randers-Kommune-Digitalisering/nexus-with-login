<script setup>
    import { inject } from 'vue';
    import Borgere from '@/components/Borgere.vue'

    const homeResource = inject('homeResource');

</script>

<template>
    <h2>Borgere</h2>
    <Borgere v-if="homeResource" :home-resource="homeResource" />

</template>
