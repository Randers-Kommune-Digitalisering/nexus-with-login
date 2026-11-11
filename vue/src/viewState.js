export const citizenListViewKey = 'citizen-list-view';

export const readCitizenListView = (storage) => {
    const saved = storage.getItem(citizenListViewKey);
    if (!saved) return null;
    try {
        const view = JSON.parse(saved);
        if (view && typeof view === 'object' && !Array.isArray(view)) return view;
    } catch (cause) {
        if (!(cause instanceof SyntaxError)) throw cause;
    }
    console.warn('Invalid saved citizen list view');
    storage.removeItem(citizenListViewKey);
    return null;
};

export const saveCitizenListView = (storage, view) => {
    const { listId, sortField, sortDirection, pageIndex, expandedPatientId } = view;
    storage.setItem(citizenListViewKey, JSON.stringify({
        listId, sortField, sortDirection, pageIndex, expandedPatientId,
    }));
};
