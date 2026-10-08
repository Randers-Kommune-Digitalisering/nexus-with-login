<script setup>
import { computed, onMounted, ref } from 'vue';

const props = defineProps({ homeResource: { type: Object, required: true } });
const citizenLists = ref([]);
const selectedId = ref('');
const patientRecords = ref([]);
const pages = ref([]);
const currentPageIndex = ref(0);
const totalItems = ref(0);
const error = ref('');
const loading = ref(true);
const fetching = ref(false);
const selectedList = computed(() => citizenLists.value.find(list => list.id === selectedId.value));
let preferencesUrl;
let contentUrl;
let selectionRequest = 0;

const loadCitizenLists = async () => {
    try {
        const configResponse = await fetch('/api/citizen-list-config');
        if (!configResponse.ok) throw new Error(`Citizen list config: HTTP ${configResponse.status}`);
        const { allowedCitizenListIds } = await configResponse.json();
        const allowedIds = new Set((allowedCitizenListIds || '')
            .split(',').map(id => id.trim()).filter(id => /^\d+$/.test(id)));
        if (!allowedIds.size) return;

        preferencesUrl = new URL(props.homeResource._links.preferences.href);
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

const fetchPatientPage = async (pageIndex) => {
    const requestId = ++selectionRequest;
    patientRecords.value = [];
    error.value = '';
    fetching.value = true;
    try {
        const href = pages.value[pageIndex]?._links?.patientData?.href;
        if (typeof href !== 'string' || !href) throw new Error('Missing patient data link');
        const patientUrl = new URL(href, contentUrl);
        const apiPrefix = preferencesUrl.pathname.slice(0, -'preferences'.length);
        if (patientUrl.origin !== preferencesUrl.origin || patientUrl.pathname !== `${apiPrefix}patients`
            || !patientUrl.searchParams.has('ids') || patientUrl.hash) {
            throw new Error('Invalid patient data link');
        }

        const response = await fetch(`/api/nexus/patients${patientUrl.search}`);
        if (!response.ok) throw new Error(`Patient data: HTTP ${response.status}`);
        const data = await response.json();
        const records = Array.isArray(data) ? data :
            [data?.patients, data?.items, data?.content, data?._embedded?.patients].find(Array.isArray);
        if (!records) throw new Error('Unexpected patient data response');
        if (requestId === selectionRequest) {
            patientRecords.value = records;
            currentPageIndex.value = pageIndex;
        }
    } catch (cause) {
        if (requestId === selectionRequest) error.value = cause.message;
    } finally {
        if (requestId === selectionRequest) fetching.value = false;
    }
};

const fetchSelected = async () => {
    const selected = selectedList.value;
    const requestId = ++selectionRequest;
    patientRecords.value = [];
    pages.value = [];
    totalItems.value = 0;
    currentPageIndex.value = 0;
    error.value = '';
    if (!selected?.href) {
        fetching.value = false;
        return;
    }

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
        const detail = await response.json();
        if (requestId !== selectionRequest) return;

        const contentHref = detail?._links?.content?.href;
        if (typeof contentHref !== 'string' || !contentHref) throw new Error('Missing citizen list content link');
        contentUrl = new URL(contentHref, target);
        const apiPrefix = preferencesUrl.pathname.slice(0, -'preferences'.length);
        const resourcePath = contentUrl.pathname.slice(apiPrefix.length);
        if (contentUrl.origin !== preferencesUrl.origin || !contentUrl.pathname.startsWith(apiPrefix)
            || !resourcePath || contentUrl.hash) {
            throw new Error('Invalid citizen list content link');
        }

        const contentResponse = await fetch(`/api/nexus/${resourcePath}${contentUrl.search}`);
        if (!contentResponse.ok) throw new Error(`Citizen list content: HTTP ${contentResponse.status}`);
        const content = await contentResponse.json();
        if (requestId !== selectionRequest) return;
        if (!Array.isArray(content.pages) || !Number.isInteger(content.totalItems) || content.totalItems < 0
            || (content.totalItems > 0 && !content.pages.length)) {
            throw new Error('Invalid citizen list pages');
        }
        pages.value = content.pages;
        totalItems.value = content.totalItems;
        if (pages.value.length) await fetchPatientPage(0);
    } catch (cause) {
        if (requestId === selectionRequest) error.value = cause.message;
    } finally {
        if (requestId === selectionRequest) fetching.value = false;
    }
};

onMounted(loadCitizenLists);

</script>

<template>
    <div class="citizen-list">
        <label for="citizen-list-select">Borgerliste</label>
        <div class="controls">
            <select id="citizen-list-select" v-model="selectedId" :disabled="loading" @change="fetchSelected">
                <option value="">Vælg en liste</option>
                <option v-for="list in citizenLists" :key="list.id" :value="list.id">{{ list.name }}</option>
            </select>
        </div>
        <p v-if="loading" role="status">Henter lister…</p>
        <p v-else-if="fetching" role="status">Henter liste…</p>
        <p v-else-if="error" role="alert">{{ error }}</p>
        <p v-else-if="!citizenLists.length" role="status">Ingen borgerlister fundet.</p>
        <p v-else-if="selectedId && !totalItems" role="status">Ingen borgere fundet.</p>
        <ol v-if="patientRecords.length" class="patient-records">
            <li v-for="(patient, index) in patientRecords" :key="patient.id ?? index">
                <pre>{{ JSON.stringify(patient, null, 2) }}</pre>
            </li>
        </ol>
        <nav v-if="pages.length > 1" class="pagination" aria-label="Borgerliste sider">
            <button type="button" :disabled="fetching || currentPageIndex === 0"
                @click="fetchPatientPage(currentPageIndex - 1)">Forrige</button>
            <span>Side {{ currentPageIndex + 1 }} af {{ pages.length }} ({{ totalItems }} borgere)</span>
            <button type="button" :disabled="fetching || currentPageIndex === pages.length - 1"
                @click="fetchPatientPage(currentPageIndex + 1)">Næste</button>
        </nav>
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
    .patient-records {
        padding-left: 1.5rem;
    }
    .patient-records li {
        border-bottom: 1px solid var(--color-border);
    }
    .pagination {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1rem;
        margin-top: 1rem;
    }
    pre {
        max-height: 30rem;
        overflow: auto;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }
</style>
