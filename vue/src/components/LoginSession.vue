<script setup>
import { onMounted, ref } from 'vue';
import Content from './Content.vue';

const emit = defineEmits(['session-change']);
const isLoggedIn = ref(false);
const userName = ref(null);
const loginError = ref('');

const checkLogin = () => {
    fetch('/api/home-ressource')
        .then(response => {
            if (response.status === 401) {
                isLoggedIn.value = false;
                userName.value = null;
                emit('session-change', null);
                return null;
            }
            if (!response.ok) throw new Error('Home resource unavailable');
            return response.json();
        })
        .then(home => {
            if (!home) return;
            userName.value = home?.professional?.fullName || null;
            emit('session-change', home);
            isLoggedIn.value = true;
        })
        .catch(() => { loginError.value = 'Kunne ikke hente brugeroplysninger.'; });
};

const loginLogout = () => {
    if (isLoggedIn.value) {
        fetch('/user/logout')
            .then(response => {
                if (response.status === 200) {
                    isLoggedIn.value = false;
                    userName.value = null;
                    emit('session-change', null);
                    loginError.value = '';
                }
            });
    } else {
        window.location.href = '/user/login';
    }
};

onMounted(checkLogin);
</script>

<template>
    <Content>
        <div class="session-controls">
            <p v-if="isLoggedIn" class="welcome"><span v-if="userName">Logget ind som <strong>{{ userName }}</strong></span></p>
            <p v-if="loginError" class="welcome" role="alert">{{ loginError }}</p>
            <button @click="loginLogout">
                {{ isLoggedIn ? 'Log ud' : 'Log ind' }}
            </button>
        </div>
    </Content>
</template>

<style scoped>
.session-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1rem;
    padding-right: 2rem;
}
.session-controls button {
    margin-left: auto;
    position: sticky;
    right: 2rem;
}
.welcome {
    margin: 0;
    font-size: 1.4rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
}
</style>