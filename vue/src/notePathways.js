export const activeNotePathways = (associations) => {
    if (!Array.isArray(associations)) throw new Error('Unexpected pathway associations response');
    const pathways = [];
    const visit = (nodes) => {
        for (const node of nodes) {
            const placement = node?.patientPathwayPlacement ?? node;
            const active = node?.patientPathwayPlacement
                ? placement.active === true : placement?.pathwayStatus === 'ACTIVE';
            if (active && Number.isSafeInteger(placement.patientPathwayId)
                && placement.patientPathwayId > 0 && typeof placement.name === 'string' && placement.name.trim()) {
                pathways.push({
                    name: placement.name,
                    programPathwayId: placement.programPathwayId,
                    pathwayTypeId: placement.pathwayTypeId,
                    parentPathwayId: placement.parentPathwayId,
                    patientPathwayId: placement.patientPathwayId,
                    active: true,
                    _links: {},
                });
            }
            if (node?.children != null) {
                if (!Array.isArray(node.children)) throw new Error('Unexpected pathway children');
                visit(node.children);
            }
        }
    };
    visit(associations);
    return pathways;
};

export const defaultNotePathway = (pathways, programPathwayId) =>
    pathways.find(pathway => pathway.programPathwayId === programPathwayId)
    ?? pathways.find(pathway => pathway.programPathwayId === 1)
    ?? pathways.find(pathway => pathway.programPathwayId === 2)
    ?? null;
