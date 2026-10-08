<script setup>
import { computed, onMounted, ref } from 'vue';

const citizenLists = ref([]);
const selectedId = ref('');
const selectedResource = ref(null);
const error = ref('');
const loading = ref(true);
const fetching = ref(false);
const selectedList = computed(() => citizenLists.value.find(list => list.id === selectedId.value));
let preferencesUrl;

const loadCitizenLists = async () => {
    try {
        const configResponse = await fetch('/api/citizen-list-config');
        if (!configResponse.ok) throw new Error(`Citizen list config: HTTP ${configResponse.status}`);
        const { allowedCitizenListIds } = await configResponse.json();
        const allowedIds = new Set((allowedCitizenListIds || '')
            .split(',').map(id => id.trim()).filter(id => /^\d+$/.test(id)));
        if (!allowedIds.size) return;

        const homeResponse = await fetch('/api/home-ressource');
        if (!homeResponse.ok) throw new Error(`Home resource: HTTP ${homeResponse.status}`);
        const home = await homeResponse.json();
        preferencesUrl = new URL(home._links.preferences.href);
        if (preferencesUrl.protocol !== 'https:' || !preferencesUrl.pathname.endsWith('/preferences')) {
            throw new Error('Invalid preferences link');
        }

        const preferencesResponse = await fetch('/api/nexus/preferences');
        if (!preferencesResponse.ok) throw new Error(`Preferences: HTTP ${preferencesResponse.status}`);
        const preferences = await preferencesResponse.json();
        if (!Array.isArray(preferences.CITIZEN_LIST)) throw new Error('Missing citizen lists');
        citizenLists.value = preferences.CITIZEN_LIST.map(({ id, name, _links }) => ({
            id: String(id), name, href: _links?.self?.href,
        })).filter(list => list.name && allowedIds.has(list.id));
    } catch (cause) {
        error.value = cause.message;
    } finally {
        loading.value = false;
    }
};

const fetchSelected = async () => {
    const selected = selectedList.value;
    if (!selected?.href) return;

    selectedResource.value = null;
    error.value = '';
    fetching.value = true;
    try {
        const target = new URL(selected.href, preferencesUrl);
        const pathPrefix = `${preferencesUrl.pathname}/CITIZEN_LIST/`;
        const id = target.pathname.slice(pathPrefix.length);
        if (target.origin !== preferencesUrl.origin || !target.pathname.startsWith(pathPrefix)
            || !/^\d+$/.test(id) || target.search || target.hash) {
            throw new Error('Invalid citizen list link');
        }

        const response = await fetch(`/api/nexus/preferences/CITIZEN_LIST/${id}`);
        if (!response.ok) throw new Error(`Citizen list: HTTP ${response.status}`);
        if (selectedId.value === selected.id) selectedResource.value = await response.json();
    } catch (cause) {
        error.value = cause.message;
    } finally {
        fetching.value = false;
    }
};

onMounted(loadCitizenLists);

</script>

<template>
    <div class="citizen-list">
        <label for="citizen-list-select">Borgerliste</label>
        <div class="controls">
            <select id="citizen-list-select" v-model="selectedId" :disabled="loading || fetching"
                @change="selectedResource = null">
                <option value="">Vælg en liste</option>
                <option v-for="list in citizenLists" :key="list.id" :value="list.id">{{ list.name }}</option>
            </select>
            <button type="button" :disabled="!selectedList?.href || loading || fetching" @click="fetchSelected">
                {{ fetching ? 'Henter…' : 'Hent liste' }}
            </button>
        </div>
        <p v-if="loading" role="status">Henter lister…</p>
        <p v-else-if="error" role="alert">{{ error }}</p>
        <p v-else-if="!citizenLists.length" role="status">Ingen borgerlister fundet.</p>
        <pre v-if="selectedResource !== null">{{ JSON.stringify(selectedResource, null, 2) }}</pre>
    </div>
</template>

<style scoped>
    .citizen-list {
        margin-top: 1rem;
        max-width: 100%;
    }
    .controls {
        display: flex;
        flex-wrap: wrap;
        align-items: flex-start;
        gap: 1rem;
    }
    select {
        flex: 1 1 24rem;
        min-width: 0;
    }
    button {
        flex: 0 0 auto;
    }
    pre {
        max-height: 30rem;
        overflow: auto;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }
</style>
