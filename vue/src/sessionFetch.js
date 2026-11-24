const maxBusyRetries = 30;
const busyRetryDelayMs = 1000;
let queue = Promise.resolve();

export async function fetchWithSessionRetry(url, options) {
    for (let attempt = 0; ; attempt++) {
        const response = await fetch(url, options);
        if (response.status !== 503 || response.headers.get('X-Session-Busy') !== '1'
            || attempt >= maxBusyRetries) return response;
        await new Promise(resolve => setTimeout(resolve, busyRetryDelayMs));
    }
}

export function queuedSessionFetch(url, options) {
    const request = queue.then(() => fetchWithSessionRetry(url, options));
    queue = request.then(() => {}, () => {});
    return request;
}
