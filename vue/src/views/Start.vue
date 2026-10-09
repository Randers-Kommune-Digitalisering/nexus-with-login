<script setup>
    import Content from '@/components/Content.vue'
    import Homeressource from '@/components/Homeressource.vue'

    import { ref } from 'vue';

    const isLoggedIn = ref(false);
    const userName = ref(null);
    const homeResource = ref(null);
    const loginError = ref('');

    const toggleLogin = () => {
        fetch('/api/home-ressource')
            .then(response => {
                if (response.status === 401) {
                    isLoggedIn.value = false;
                    userName.value = null;
                    homeResource.value = null;
                    return null;
                }
                if (!response.ok) throw new Error('Home resource unavailable');
                return response.json();
            })
            .then(home => {
                if (!home) return;
                userName.value = home?.professional?.fullName || null;
                homeResource.value = home;
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
                        homeResource.value = null;
                        loginError.value = '';
                    }
                });
        } else {
            window.location.href = '/user/login';
        }
    };

    toggleLogin();

</script>

<template>
    <h2>Randers Nexus</h2>

    <Content>
        <div class="session-controls">
            <p v-if="isLoggedIn" class="welcome"><span v-if="userName">Logget ind som <strong>{{ userName }}</strong></span></p>
            <button @click="loginLogout">
            {{ isLoggedIn ? 'Log ud' : 'Log ind' }}
            </button>
        </div>
        <p v-if="loginError" role="alert">{{ loginError }}</p>
    </Content>
    <Homeressource v-if="isLoggedIn" :home-resource="homeResource" />

</template>

<style scoped>
.session-controls {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
}
.welcome {
    margin: 0;
    font-size: 1.4rem;
    line-height: 1.4;
    overflow-wrap: anywhere;
}
</style>