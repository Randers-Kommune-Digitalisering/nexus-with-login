<script setup>
import { ref } from 'vue';

const homeRessource = ref(null);

const fetchHome = () => {
    fetch('/api/home-ressource')
        .then(response => response.json())
        .then(data => {
            homeRessource.value = data;
        })
        .catch(error => {
            console.error('Error fetching home resource:', error);
        });
};

// Fetch home ressource on component mount
fetchHome();

</script>

<template>
    Home Ressource
    
    <div>
        <pre>{{ homeRessource }}</pre>        
    </div>
</template>

<style scoped>
    div
    {
        margin-top: 1rem;
        padding-left: 1.5rem;
        border-left: 0.1rem solid var(--color-border);
    }
</style>
