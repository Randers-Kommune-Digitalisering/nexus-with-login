import assert from 'node:assert/strict';
import { test } from 'node:test';
import { citizenListViewKey, readCitizenListView, saveCitizenListView } from './viewState.js';

const storage = () => {
    const values = new Map();
    return {
        getItem: key => values.get(key) ?? null,
        setItem: (key, value) => values.set(key, value),
        removeItem: key => values.delete(key),
    };
};

test('stores only view choices, not patient records or note contents', () => {
    const tab = storage();
    saveCitizenListView(tab, {
        listId: '5327', sortField: 'name', sortDirection: 'descending',
        pageIndex: 1, expandedPatientId: '11',
        notes: [{ text: 'not for browser storage' }],
        patientRecords: [{ id: 11 }],
    });

    assert.deepEqual(readCitizenListView(tab), {
        listId: '5327', sortField: 'name', sortDirection: 'descending',
        pageIndex: 1, expandedPatientId: '11',
    });
    assert.ok(!tab.getItem(citizenListViewKey).includes('not for browser storage'));
});

test('discards malformed saved state', (context) => {
    const tab = storage();
    tab.setItem(citizenListViewKey, '{');

    const warning = context.mock.method(console, 'warn', () => {});
    assert.equal(readCitizenListView(tab), null);
    assert.equal(warning.mock.callCount(), 1);
    assert.equal(tab.getItem(citizenListViewKey), null);
});
