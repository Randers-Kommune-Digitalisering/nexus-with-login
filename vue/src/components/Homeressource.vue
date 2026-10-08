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
const additionalInfoKeys = computed(() => [...new Set(
    patientRecords.value.flatMap(patient => Object.keys(patient.additionalInfo ?? {}).filter(key => key.toLowerCase() !== 'tekst'))
)]);
const visiblePages = computed(() => {
    const start = Math.min(Math.max(currentPageIndex.value - 2, 0), Math.max(pages.value.length - 5, 0));
    return Array.from({ length: Math.min(pages.value.length, 5) }, (_, index) => start + index);
});
const formatAddress = (address) => {
    if (!address) return '';
    const lines = [1, 2, 3, 4, 5]
        .map(index => String(address[`addressLine${index}`] ?? '').trim().replace(/,+$/, '').trim())
        .filter(Boolean);
    const locality = [address.postalCode, address.postalDistrict]
        .map(value => String(value ?? '').trim()).filter(Boolean).join(' ');
    return [...lines, locality].filter(Boolean).join(', ');
};
const formatTime = (timestamp) => {
    if (!Number.isFinite(timestamp)) return '';
    const parts = Object.fromEntries(new Intl.DateTimeFormat('da-DK', {
        timeZone: 'Europe/Copenhagen', day: '2-digit', month: '2-digit', year: '2-digit',
        hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(timestamp).map(({ type, value }) => [type, value]));
    return `${parts.day}/${parts.month}/${parts.year} ${parts.hour}:${parts.minute}`;
};
let preferencesUrl;
let contentUrl;
let selectionRequest = 0;

const additionalInfoForPatient = async (patient) => {
    const patientId = String(patient?.id ?? '');
    if (!/^\d+$/.test(patientId)) return { additionalInfo: {}, referenceDate: null };
    const url = `/api/nexus/patients/${patientId}/pathways/flatReferences?filterId=749`;
    try {
        const response = await fetch(url);
        if (!response.ok) return { additionalInfo: {}, referenceDate: null };
        const references = await response.json();
        if (!Array.isArray(references)) return { additionalInfo: {}, referenceDate: null };
        const latest = references.reduce((newest, entry) => {
            const date = Date.parse(String(entry?.date ?? '').replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
            return Number.isFinite(date) && (!newest || date > newest.date) ? { entry, date } : newest;
        }, null);
        if (!Array.isArray(latest?.entry?.additionalInfo)) return { additionalInfo: {}, referenceDate: latest?.date ?? null };
        return { referenceDate: latest.date, additionalInfo: Object.fromEntries(latest.entry.additionalInfo
            .filter(item => item?.type === 'keyValue' && typeof item.key === 'string' && item.key.trim())
            .map(({ key, value }) => [key.trim().replace(/:+$/, ''), value ?? ''])) };
    } catch {
        return { additionalInfo: {}, referenceDate: null };
    }
};

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
        if (requestId !== selectionRequest) return;
        const rows = await Promise.all(records.map(async patient => ({
            ...patient,
            ...await additionalInfoForPatient(patient),
        })));
        if (requestId === selectionRequest) {
            patientRecords.value = rows;
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
        <div v-if="patientRecords.length" class="table-scroll">
            <table class="patient-table">
                <thead>
                    <tr>
                        <th scope="col" class="single-line">CPR</th>
                        <th scope="col" class="single-line">Navn</th>
                        <th scope="col">Adresse</th>
                        <th scope="col" class="single-line">Hjemmetelefon</th>
                        <th scope="col" class="single-line">Mobiltelefon</th>
                        <th scope="col" class="single-line">Arbejdstelefon</th>
                        <th v-for="key in additionalInfoKeys" :key="key" scope="col">{{ key }}</th>
                        <th scope="col" class="single-line">Tid</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(patient, index) in patientRecords" :key="patient.id ?? index">
                        <td class="single-line">{{ patient.patientIdentifier?.identifier }}</td>
                        <td><span class="name-text">{{ patient.fullReversedName }}</span></td>
                        <td><span class="address-text">{{ formatAddress(patient.currentAddress) }}</span></td>
                        <td class="single-line">{{ patient.homePhoneNumber }}</td>
                        <td class="single-line">{{ patient.mobilePhoneNumber }}</td>
                        <td class="single-line">{{ patient.workPhoneNumber }}</td>
                        <td v-for="key in additionalInfoKeys" :key="key">
                            <span class="clamped extra-text">{{ patient.additionalInfo?.[key] }}</span>
                        </td>
                        <td class="single-line">{{ formatTime(patient.referenceDate) }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        <nav v-if="pages.length > 1" class="pagination" aria-label="Borgerliste sider">
            <button type="button" :disabled="fetching || currentPageIndex === 0"
                :class="{ disabled: fetching || currentPageIndex === 0 }"
                aria-label="Forrige side" @click="fetchPatientPage(currentPageIndex - 1)">&lt;</button>
            <button v-for="pageIndex in visiblePages" :key="pageIndex" type="button"
                :class="{ selected: currentPageIndex === pageIndex, disabled: fetching }"
                :disabled="fetching || currentPageIndex === pageIndex"
                :aria-current="currentPageIndex === pageIndex ? 'page' : undefined"
                @click="fetchPatientPage(pageIndex)">{{ pageIndex + 1 }}</button>
            <button type="button" :disabled="fetching || currentPageIndex === pages.length - 1"
                :class="{ disabled: fetching || currentPageIndex === pages.length - 1 }"
                aria-label="Næste side" @click="fetchPatientPage(currentPageIndex + 1)">&gt;</button>
        </nav>
        <p v-if="pages.length > 1" class="page-summary">{{ totalItems }} borgere</p>
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
    .table-scroll {
        max-width: 100%;
        overflow-x: auto;
    }
    .patient-table {
        width: 100%;
        min-width: 78rem;
        border-collapse: collapse;
    }
    .patient-table th, .patient-table td {
        text-align: left;
        vertical-align: top;
        overflow-wrap: anywhere;
    }
    .patient-table th {
        white-space: nowrap;
        overflow-wrap: normal;
    }
    .patient-table th:not(:last-child), .patient-table td:not(:last-child) {
        padding-right: 0.5rem;
    }
    .single-line {
        white-space: nowrap;
        overflow-wrap: normal;
    }
    .clamped {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
        overflow-wrap: anywhere;
    }
    .name-text {
        display: block;
        width: 11rem;
        overflow-wrap: anywhere;
    }
    .address-text {
        display: block;
        width: 16rem;
        overflow-wrap: anywhere;
    }
    .extra-text {
        max-width: 22rem;
        -webkit-line-clamp: 2;
    }
    .pagination {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 1rem;
    }
    .pagination > button {
        font: inherit;
        font-weight: 400;
        letter-spacing: 0;
        text-transform: none;
        height: auto;
        line-height: 1.2;
        margin: 0;
        padding: 0.5em 1rem;
        border: 0.1rem solid var(--color-border);
        background-color: var(--color-bg);
        color: var(--color-text);
        border-radius: 0;
    }
    .pagination > button:first-child {
        border-radius: 0.5rem 0 0 0.5rem;
    }
    .pagination > button:last-child {
        border-radius: 0 0.5rem 0.5rem 0;
    }
    .pagination > button:disabled {
        background-color: var(--color-bg) !important;
    }
    .pagination > button.selected:disabled {
        background-color: var(--color-border) !important;
    }
    .page-summary {
        margin-top: 0.5rem;
        text-align: center;
    }
</style>
