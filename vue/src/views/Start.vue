<script setup>
    import Content from '@/components/Content.vue'
    import Status from '@/components/Status.vue'
    import Homeressource from '@/components/Homeressource.vue'

    import IconOK from '@/components/icons/IconOK.vue'
    import IconRSS from '@/components/icons/IconRSS.vue'
    import { ref } from 'vue';

    const isLoggedIn = ref(false);
    const userName = ref(null);
    const statusRef = ref(null);

    const toggleLogin = () => {

        fetch('/user/profile')
            .then(response => {
                console.log('Response status:', response.status);
                if (response.status === 401) {
                    isLoggedIn.value = false;
                } else if (response.status === 200) {
                    response.json()
                        .then(data => {
                            userName.value = data.given_name;
                            isLoggedIn.value = true;
                            statusRef.value.fetchStatus();
                        });
                }
            })
    };

    const loginLogout = () => {
        if (isLoggedIn.value) {
            fetch('/user/logout')
                .then(response => {
                    console.log('Response status:', response.status);
                    if (response.status === 200) {
                        isLoggedIn.value = false;
                        statusRef.value.fetchStatus();
                    }
                });
        } else {
            window.location.href = '/user/login';
        }
    };

    toggleLogin();

</script>

<template>
    <h2>Flask + Vue Template</h2>

    <Content>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 v-if="isLoggedIn" style="margin: 0;">Hej {{ userName }}</h3>
            <button @click="loginLogout">
            {{ isLoggedIn ? 'Logout' : 'Login' }}
            </button>
        </div>
    </Content>
    
    <Content>
        <template #icon>
            <IconOK />
        </template>
        <template #heading>Sådan, det ser ud til at køre!</template>
        
        Du har nu succesfuldt startet et nyt projekt med <a href="https://github.com/Randers-Kommune-Digitalisering/vue-python-template" target="_blank" rel="noopener">Randers Kommune's Flask + Vue template</a>.
    </Content>

    <Content>
        <template #icon>
            <IconRSS />
        </template>
        <template #heading>Status på opsætning</template>
        
        <Status ref="statusRef" />
        <Homeressource />
    </Content>

</template>