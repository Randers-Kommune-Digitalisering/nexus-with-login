<script setup>
import { computed, onMounted, ref, toRaw } from 'vue';
import { ChevronDown, ChevronUp, Pencil, Plus } from '@lucide/vue';

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
const expandedRowIndex = ref(null);
const editingNoteKey = ref(null);
const editState = ref(null);
const editLoading = ref(false);
const editSaving = ref(false);
const editError = ref('');
const editChanged = computed(() => editState.value && (
    editState.value.subject !== editState.value.originalSubject
    || editState.value.text !== editState.value.originalText
));
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
let editRequest = 0;

const nexusLink = (href, base) => {
    if (typeof href !== 'string' || !href) throw new Error('Missing Nexus link');
    const target = new URL(href, base);
    const apiPrefix = preferencesUrl.pathname.slice(0, -'preferences'.length);
    if (target.protocol !== 'https:' || target.origin !== preferencesUrl.origin
        || !target.pathname.startsWith(apiPrefix) || target.hash) {
        throw new Error('Invalid Nexus link');
    }
    return { url: target, proxy: `/api/nexus/${target.pathname.slice(apiPrefix.length)}${target.search}` };
};

const cancelEdit = () => {
    ++editRequest;
    editingNoteKey.value = null;
    editState.value = null;
    editLoading.value = false;
    editError.value = '';
};

const toggleRow = (index) => {
    if (editSaving.value) return;
    cancelEdit();
    expandedRowIndex.value = expandedRowIndex.value === index ? null : index;
};

const editNote = async (patient, note, rowIndex, noteIndex) => {
    if (!note.referencedObjectHref || editSaving.value) return;
    cancelEdit();
    const requestId = editRequest;
    editingNoteKey.value = `${rowIndex}:${noteIndex}`;
    editLoading.value = true;
    let failureMessage = 'Kunne ikke hente sagsnotens formular.';
    try {
        const source = nexusLink(note.sourceHref, new URL('./', preferencesUrl));
        const formLink = nexusLink(note.referencedObjectHref, source.url);
        const formResponse = await fetch(formLink.proxy);
        if (!formResponse.ok) {
            failureMessage = `Kunne ikke hente sagsnotens formular (HTTP ${formResponse.status}).`;
            throw new Error(failureMessage);
        }
        const form = await formResponse.json();
        const items = form?.formDefinition?.items;
        const subjectItem = Array.isArray(items) && items.find(item => item.label === 'Emne:');
        const textItem = Array.isArray(items) && items.find(item => item.label === 'Tekst:');
        failureMessage = 'Formularen mangler Emne: eller Tekst:.';
        if (!subjectItem || !textItem) throw new Error('Missing note fields');

        failureMessage = 'Formularens availableActions-link mangler eller er ugyldigt.';
        const actionsLink = nexusLink(form.formDefinition._links?.availableActions?.href, formLink.url);
        failureMessage = 'Kunne ikke hente formularens handlinger.';
        const actionsResponse = await fetch(actionsLink.proxy);
        if (!actionsResponse.ok) {
            failureMessage = `Kunne ikke hente formularens handlinger (HTTP ${actionsResponse.status}).`;
            throw new Error(failureMessage);
        }
        const actions = await actionsResponse.json();
        failureMessage = 'Handlingssvaret er ikke en liste.';
        if (!Array.isArray(actions)) throw new Error('Unexpected actions response');
        failureMessage = 'Handlingen Udfyldt blev ikke fundet.';
        const completedAction = actions.find(action => action?.name === 'Udfyldt');
        if (!completedAction) throw new Error('Missing completed action');
        failureMessage = 'Udfyldt mangler et gyldigt updateFormData-link.';
        const updateLink = nexusLink(completedAction?._links?.updateFormData?.href, actionsLink.url);
        if (requestId !== editRequest) return;

        const subject = String(subjectItem.value ?? '');
        const text = String(textItem.value ?? '');
        editState.value = {
            form, patient, note, updateProxy: updateLink.proxy,
            etag: formResponse.headers.get('ETag'),
            originalSubject: subject, originalText: text, subject, text,
        };
    } catch {
        if (requestId === editRequest) editError.value = failureMessage;
    } finally {
        if (requestId === editRequest) editLoading.value = false;
    }
};

const saveNote = async () => {
    if (!editState.value || !editChanged.value || editSaving.value) return;
    const state = editState.value;
    const payload = structuredClone(toRaw(state.form));
    payload.formDefinition.items.find(item => item.label === 'Emne:').value = state.subject;
    payload.formDefinition.items.find(item => item.label === 'Tekst:').value = state.text;
    editSaving.value = true;
    editError.value = '';
    try {
        const csrfResponse = await fetch('/api/csrf');
        if (!csrfResponse.ok) throw new Error('Could not get CSRF token');
        const { token } = await csrfResponse.json();
        if (typeof token !== 'string' || !token) throw new Error('Missing CSRF token');
        const response = await fetch(state.updateProxy, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token,
                ...(state.etag ? { 'If-Match': state.etag } : {}),
            },
            body: JSON.stringify(payload),
        });
        if (!response.ok) throw new Error('Could not update note');
        state.note.subject = state.subject;
        state.note.text = state.text;
        if (state.note.date === state.patient.referenceDate) {
            const subjectKey = Object.keys(state.patient.additionalInfo).find(key => key.toLowerCase() === 'emne') ?? 'Emne';
            state.patient.additionalInfo[subjectKey] = state.subject;
        }
        cancelEdit();
    } catch {
        editError.value = 'Kunne ikke gemme sagsnoten. Prøv igen.';
    } finally {
        editSaving.value = false;
    }
};

const additionalInfoForPatient = async (patient) => {
    const patientId = String(patient?.id ?? '');
    if (!/^\d+$/.test(patientId)) return { additionalInfo: {}, referenceDate: null, notes: [] };
    const url = `/api/nexus/patients/${patientId}/pathways/flatReferences?filterId=749`;
    try {
        const response = await fetch(url);
        if (!response.ok) return { additionalInfo: {}, referenceDate: null, notes: [] };
        const references = await response.json();
        if (!Array.isArray(references)) return { additionalInfo: {}, referenceDate: null, notes: [] };
        const sourceUrl = new URL(`patients/${patientId}/pathways/flatReferences?filterId=749`, new URL('./', preferencesUrl));
        const notes = references.map(entry => {
            const parsedDate = Date.parse(String(entry?.date ?? '').replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
            const fields = Object.fromEntries((Array.isArray(entry?.additionalInfo) ? entry.additionalInfo : [])
                .filter(item => item?.type === 'keyValue' && typeof item.key === 'string' && item.key.trim())
                .map(({ key, value }) => [key.trim().replace(/:+$/, '').toLowerCase(), value ?? '']));
            return {
                subject: fields.emne ?? '', text: fields.tekst ?? '',
                date: Number.isFinite(parsedDate) ? parsedDate : null,
                referencedObjectHref: entry?._links?.referencedObject?.href,
                sourceHref: new URL(entry?._links?.self?.href ?? sourceUrl.href, sourceUrl).href,
            };
        }).sort((first, second) => (second.date ?? -Infinity) - (first.date ?? -Infinity));
        const latest = references.reduce((newest, entry) => {
            const date = Date.parse(String(entry?.date ?? '').replace(/([+-]\d{2})(\d{2})$/, '$1:$2'));
            return Number.isFinite(date) && (!newest || date > newest.date) ? { entry, date } : newest;
        }, null);
        if (!Array.isArray(latest?.entry?.additionalInfo)) return { additionalInfo: {}, referenceDate: latest?.date ?? null, notes };
        return { referenceDate: latest.date, additionalInfo: Object.fromEntries(latest.entry.additionalInfo
            .filter(item => item?.type === 'keyValue' && typeof item.key === 'string' && item.key.trim())
            .map(({ key, value }) => [key.trim().replace(/:+$/, ''), value ?? ''])), notes };
    } catch {
        return { additionalInfo: {}, referenceDate: null, notes: [] };
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
    cancelEdit();
    patientRecords.value = [];
    expandedRowIndex.value = null;
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
    cancelEdit();
    patientRecords.value = [];
    expandedRowIndex.value = null;
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
            <select id="citizen-list-select" v-model="selectedId" :disabled="loading || editSaving" @change="fetchSelected">
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
                        <th scope="col" class="row-action"><span class="visually-hidden">Sagsnoter</span></th>
                    </tr>
                </thead>
                <tbody>
                    <template v-for="(patient, index) in patientRecords" :key="patient.id ?? index">
                    <tr>
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
                        <td class="row-action">
                            <button type="button" class="icon-button" :disabled="editSaving" :aria-expanded="expandedRowIndex === index"
                                :aria-controls="`patient-notes-${index}`" :aria-label="`${expandedRowIndex === index ? 'Skjul' : 'Vis'} sagsnoter for ${patient.fullReversedName}`"
                                @click="toggleRow(index)">
                                <ChevronUp v-if="expandedRowIndex === index" aria-hidden="true" />
                                <ChevronDown v-else aria-hidden="true" />
                            </button>
                        </td>
                    </tr>
                    <tr v-if="expandedRowIndex === index" :id="`patient-notes-${index}`" class="notes-row">
                        <td :colspan="8 + additionalInfoKeys.length">
                            <div class="notes-panel">
                                <button type="button" class="add-note" disabled aria-label="Tilføj sagsnote (ikke klar endnu)">
                                    <Plus aria-hidden="true" /> Tilføj sagsnote
                                </button>
                                <table v-if="patient.notes?.length" class="notes-table">
                                    <thead>
                                        <tr>
                                            <th scope="col">Emne</th>
                                            <th scope="col">Tekst</th>
                                            <th scope="col">Tid</th>
                                            <th scope="col"><span class="visually-hidden">Rediger</span></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <template v-for="(note, noteIndex) in patient.notes" :key="noteIndex">
                                        <tr>
                                            <td>{{ note.subject }}</td>
                                            <td class="note-text">{{ note.text }}</td>
                                            <td class="single-line">{{ formatTime(note.date) }}</td>
                                            <td class="row-action">
                                                <button type="button" class="icon-button" :disabled="!note.referencedObjectHref || editSaving"
                                                    aria-label="Rediger sagsnote" title="Rediger sagsnote"
                                                    @click="editNote(patient, note, index, noteIndex)">
                                                    <Pencil aria-hidden="true" />
                                                </button>
                                            </td>
                                        </tr>
                                        <tr v-if="editingNoteKey === `${index}:${noteIndex}`" class="note-editor-row">
                                            <td colspan="4">
                                                <p v-if="editLoading" role="status">Henter sagsnote…</p>
                                                <form v-else-if="editState" class="note-editor" @submit.prevent="saveNote">
                                                    <label :for="`note-subject-${index}-${noteIndex}`">Emne</label>
                                                    <input :id="`note-subject-${index}-${noteIndex}`" v-model="editState.subject" type="text">
                                                    <label :for="`note-text-${index}-${noteIndex}`">Tekst</label>
                                                    <textarea :id="`note-text-${index}-${noteIndex}`" v-model="editState.text"></textarea>
                                                    <div class="note-editor-actions">
                                                        <button type="submit" :disabled="!editChanged || editSaving">{{ editSaving ? 'Gemmer…' : 'Gem' }}</button>
                                                        <button type="button" :disabled="editSaving" @click="cancelEdit">Annuller</button>
                                                    </div>
                                                </form>
                                                <p v-if="editError" role="alert">{{ editError }}</p>
                                            </td>
                                        </tr>
                                        </template>
                                    </tbody>
                                </table>
                                <p v-else>Ingen sagsnoter fundet.</p>
                            </div>
                        </td>
                    </tr>
                    </template>
                </tbody>
            </table>
        </div>
        <nav v-if="pages.length > 1" class="pagination" aria-label="Borgerliste sider">
            <button type="button" :disabled="fetching || editSaving || currentPageIndex === 0"
                :class="{ disabled: fetching || editSaving || currentPageIndex === 0 }"
                aria-label="Forrige side" @click="fetchPatientPage(currentPageIndex - 1)">&lt;</button>
            <button v-for="pageIndex in visiblePages" :key="pageIndex" type="button"
                :class="{ selected: currentPageIndex === pageIndex, disabled: fetching || editSaving }"
                :disabled="fetching || editSaving || currentPageIndex === pageIndex"
                :aria-current="currentPageIndex === pageIndex ? 'page' : undefined"
                @click="fetchPatientPage(pageIndex)">{{ pageIndex + 1 }}</button>
            <button type="button" :disabled="fetching || editSaving || currentPageIndex === pages.length - 1"
                :class="{ disabled: fetching || editSaving || currentPageIndex === pages.length - 1 }"
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
        width: max-content;
        min-width: 100%;
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
    .row-action {
        width: 4rem;
        text-align: right !important;
        white-space: nowrap;
    }
    .icon-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 3rem;
        height: 3rem;
        padding: 0;
        margin: 0;
        border: 0;
        background: transparent;
        color: var(--color-text);
    }
    .icon-button:disabled, .add-note:disabled {
        background: transparent !important;
        color: var(--color-text);
        opacity: 0.55;
    }
    .icon-button svg, .add-note svg {
        width: 1.7rem;
        height: 1.7rem;
    }
    .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
    }
    .notes-row > td {
        padding: 1rem;
        background: var(--color-bg);
    }
    .notes-panel {
        contain: inline-size;
        max-width: 100%;
    }
    .add-note {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .notes-table {
        width: 100%;
        table-layout: fixed;
    }
    .notes-table th:nth-child(1) {
        width: 16rem;
    }
    .notes-table th:nth-child(3) {
        width: 14rem;
    }
    .notes-table th:nth-child(4) {
        width: 4rem;
    }
    .note-text {
        white-space: pre-wrap;
    }
    .note-editor-row > td {
        padding: 1rem 0;
    }
    .note-editor label {
        display: block;
        margin-bottom: 0.4rem;
    }
    .note-editor input {
        display: block;
        width: min(100%, 32rem);
    }
    .note-editor textarea {
        display: block;
        width: 100%;
        min-height: 10rem;
        resize: vertical;
    }
    .note-editor-actions {
        display: flex;
        gap: 0.5rem;
    }
    .note-editor-actions button {
        margin: 0;
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
