<script setup>
import { ref } from 'vue';

const statusFlask = ref(null);

const fetchStatus = () => {
    fetch('/api/status')
        .then(response => response.json())
        .then(value => statusFlask.value = value.success ? "Connected" : null)
        .then(value => console.log("Flask status: \n" + value));
};

// Fetch status on component mount
fetchStatus();

// Expose the fetchStatus method to the parent
defineExpose({
    fetchStatus
});
</script>

<template>
    Herunder kan du se om din Flask backend kører. Vær opmærksom på at Flask serveren ikke kører hvis du bruger Vite i udviklingsmiljø.
    
    <div>
        <span>Flask</span>:
        <span v-if="statusFlask" class="green heavy">{{statusFlask}}</span>
        <span v-else="statusNodered" class="red heavy">Not connected</span>
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
