// Injected by the iOS app at document start. Replaces the browser features a
// WKWebView doesn't provide (downloads, file pickers, the async clipboard) with
// calls to the native side, and tidies up a few things for touch screens.
(function () {
    'use strict';

    const handler = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.bfxr;
    if (!handler) return;

    function call(action, payload) {
        return handler.postMessage(Object.assign({ action: action }, payload || {}));
    }

    // ---- diagnostics: forward uncaught errors so they show up in the Xcode console.
    window.__bfxrErrors = [];
    window.addEventListener('error', function (e) {
        const message = (e.message || 'error') + ' @ ' + (e.filename || '') + ':' + (e.lineno || 0);
        window.__bfxrErrors.push(message);
        call('log', { level: 'error', message: message }).catch(function () {});
    });
    window.addEventListener('unhandledrejection', function (e) {
        const message = 'unhandled rejection: ' + (e.reason && (e.reason.stack || e.reason.message) || e.reason);
        window.__bfxrErrors.push(message);
        call('log', { level: 'error', message: message }).catch(function () {});
    });

    // ---- links copied with "Copy Link" should open the public web version.
    window.BFXR_SHARE_URL = 'https://www.bfxr.net/';

    // ---- audio: play through the silent switch, and wake the context on return.
    try {
        if (navigator.audioSession) navigator.audioSession.type = 'playback';
    } catch (e) { /* not available before iOS 17 */ }
    function resumeAudio() {
        const ctx = window.AUDIO_CONTEXT;
        if (ctx && ctx.state !== 'running' && ctx.resume) ctx.resume().catch(function () {});
    }
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) resumeAudio();
    });
    document.addEventListener('touchend', resumeAudio, { capture: true, passive: true });
    window.__bfxrResumeAudio = resumeAudio;

    // ---- clipboard: custom-scheme pages aren't a secure context, so provide our own.
    const clipboard = {
        writeText: function (text) {
            return call('clipboardWrite', { text: String(text) }).then(function () {});
        },
        readText: function () {
            return call('clipboardRead').then(function (text) { return text || ''; });
        }
    };
    try {
        Object.defineProperty(navigator, 'clipboard', { value: clipboard, configurable: true });
    } catch (e) {
        console.error('could not install clipboard bridge', e);
    }

    // ---- downloads: <a download> becomes the iOS share sheet.
    function blobToBase64(blob) {
        return new Promise(function (resolve, reject) {
            const reader = new FileReader();
            reader.onload = function () {
                const url = String(reader.result);
                resolve(url.slice(url.indexOf(',') + 1));
            };
            reader.onerror = function () { reject(reader.error); };
            reader.readAsDataURL(blob);
        });
    }

    function saveLink(anchor) {
        const href = anchor.href;
        const filename = anchor.getAttribute('download') || 'download';
        return fetch(href)
            .then(function (response) { return response.blob(); })
            .then(function (blob) {
                return blobToBase64(blob).then(function (base64) {
                    return call('saveFile', { filename: filename, mimeType: blob.type, base64: base64 });
                });
            })
            .catch(function (e) {
                console.error('could not save ' + filename, e);
                alert('Could not save ' + filename + '.');
            });
    }

    function isDownloadLink(anchor) {
        return anchor.hasAttribute('download') && anchor.href && !/^#|#$/.test(anchor.getAttribute('href') || '#');
    }

    const anchorClick = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
        if (isDownloadLink(this)) {
            saveLink(this);
            return;
        }
        return anchorClick.apply(this, arguments);
    };
    document.addEventListener('click', function (e) {
        const anchor = e.target && e.target.closest && e.target.closest('a[download]');
        if (anchor && isDownloadLink(anchor)) {
            e.preventDefault();
            saveLink(anchor);
        }
    }, true);

    // ---- opening files: <input type=file> becomes the iOS document picker.
    function base64ToBytes(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        return bytes;
    }

    function deliverFiles(input, files) {
        const list = files.map(function (f) {
            return new File([base64ToBytes(f.base64)], f.name, { type: f.mimeType || '' });
        });
        try {
            const transfer = new DataTransfer();
            list.forEach(function (file) { transfer.items.add(file); });
            input.files = transfer.files;
        } catch (e) {
            Object.defineProperty(input, 'files', { value: list, configurable: true });
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const inputClick = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function () {
        if (this.type !== 'file') return inputClick.apply(this, arguments);
        const input = this;
        call('openFile', { accept: input.accept || '', multiple: !!input.multiple })
            .then(function (files) {
                if (files && files.length) deliverFiles(input, files);
            })
            .catch(function (e) { console.error('could not open file', e); });
    };

    // ---- files handed to the app from elsewhere (Files, AirDrop, "Open in Bfxr").
    function whenReady(fn) {
        if (document.readyState === 'complete' && typeof SaveLoad !== 'undefined') fn();
        else window.addEventListener('load', fn, { once: true });
    }
    window.__bfxrOpenDocument = function (name, base64) {
        whenReady(function () {
            const text = new TextDecoder().decode(base64ToBytes(base64));
            const lower = name.toLowerCase();
            if (lower.endsWith('.bcol')) {
                SaveLoad.load_serialized_collection(text);
            } else if (lower.endsWith('.bfxr')) {
                SaveLoad.load_serialized_synth(text);
            } else {
                alert('Bfxr can open .bfxr and .bcol files, not ' + name + '.');
                return;
            }
            SaveLoad.save_all_collections();
        });
    };

    // ---- touch tidying.
    const style = document.createElement('style');
    style.textContent = [
        'html { -webkit-touch-callout: none; -webkit-tap-highlight-color: transparent; touch-action: manipulation; }',
        'textarea, input[type=text], input:not([type]) { -webkit-user-select: text; user-select: text; }'
    ].join('\n');
    function addStyle() {
        document.documentElement.appendChild(style);
        document.documentElement.classList.add('bfxr-ios');
    }
    if (document.documentElement) addStyle();
    else document.addEventListener('DOMContentLoaded', addStyle, { once: true });

    document.addEventListener('DOMContentLoaded', function () {
        // App Store rules don't allow links to outside payment pages, so drop the
        // sponsorship links from the footer while keeping the rest.
        const footer = document.getElementById('footer');
        if (!footer) return;
        const links = Array.prototype.filter.call(footer.querySelectorAll('a'), function (a) {
            return !/sponsors|paypal/i.test(a.href);
        });
        footer.textContent = '';
        links.forEach(function (a, i) {
            if (i) footer.appendChild(document.createTextNode(' · '));
            footer.appendChild(a);
        });
    });
})();
