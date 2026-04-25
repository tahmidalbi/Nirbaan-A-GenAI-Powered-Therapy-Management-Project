/**
 * E2EE crypto utilities for EP-Patient direct chat.
 *
 * Key exchange: ECDH P-256 (each user generates one key pair, persisted in IndexedDB)
 * Encryption:   AES-GCM 256-bit with a random 96-bit IV per message
 *
 * Private keys never leave the device. The server only stores public key JWKs and
 * relays opaque ciphertext blobs — it cannot read message content.
 */

const IDB_NAME = 'nirbaan_e2ee';
const IDB_VERSION = 1;
const STORE = 'keys';
const KEYPAIR_KEY = 'ep_patient_keypair';

// ── IndexedDB helpers ──────────────────────────────────────────────────────

function openIDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, IDB_VERSION);
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore(STORE);
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = () => reject(req.error);
  });
}

function idbGet(db, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const req = tx.objectStore(STORE).get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbPut(db, key, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const req = tx.objectStore(STORE).put(value, key);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ── Base64 helpers ─────────────────────────────────────────────────────────

function bufToB64(buffer) {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

function b64ToBuf(b64) {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)).buffer;
}

// ── Key management ─────────────────────────────────────────────────────────

/**
 * Returns an ECDH key pair for this user.
 * On first call: generates a P-256 key pair, stores both JWKs in IndexedDB,
 * returns { privateKey: CryptoKey, publicKeyJwk: object }.
 * On subsequent calls (including page reloads): reimports the stored private key.
 */
export async function getOrCreateKeyPair() {
  const db = await openIDB();
  const stored = await idbGet(db, KEYPAIR_KEY);

  if (stored?.privateKeyJwk && stored?.publicKeyJwk) {
    const privateKey = await crypto.subtle.importKey(
      'jwk',
      stored.privateKeyJwk,
      { name: 'ECDH', namedCurve: 'P-256' },
      false,
      ['deriveKey'],
    );
    return { privateKey, publicKeyJwk: stored.publicKeyJwk };
  }

  // Generate fresh key pair
  const keyPair = await crypto.subtle.generateKey(
    { name: 'ECDH', namedCurve: 'P-256' },
    true, // extractable — needed to store as JWK
    ['deriveKey'],
  );

  const [publicKeyJwk, privateKeyJwk] = await Promise.all([
    crypto.subtle.exportKey('jwk', keyPair.publicKey),
    crypto.subtle.exportKey('jwk', keyPair.privateKey),
  ]);

  await idbPut(db, KEYPAIR_KEY, { privateKeyJwk, publicKeyJwk });
  return { privateKey: keyPair.privateKey, publicKeyJwk };
}

// ── Key agreement ──────────────────────────────────────────────────────────

/**
 * Derives a shared AES-GCM 256-bit key from your private key and the peer's
 * public key JWK. Both parties independently derive the same key (ECDH).
 */
export async function deriveSharedKey(myPrivateKey, theirPublicKeyJwk) {
  const theirPublicKey = await crypto.subtle.importKey(
    'jwk',
    theirPublicKeyJwk,
    { name: 'ECDH', namedCurve: 'P-256' },
    false,
    [],
  );
  return crypto.subtle.deriveKey(
    { name: 'ECDH', public: theirPublicKey },
    myPrivateKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

// ── Encrypt / Decrypt ──────────────────────────────────────────────────────

/**
 * Encrypts a plaintext string.
 * Returns { e2ee: true, iv: string, ciphertext: string } (all base64).
 * Serialize this as JSON and put it in the message `content` field.
 */
export async function encryptMsg(sharedKey, plaintext) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const encoded = new TextEncoder().encode(plaintext);
  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    sharedKey,
    encoded,
  );
  return {
    e2ee: true,
    iv: bufToB64(iv),
    ciphertext: bufToB64(ciphertext),
  };
}

/**
 * Decrypts a message object if its `content` is an E2EE payload.
 * Returns a new message object with plaintext in `.content`.
 * Falls back silently to the original message if sharedKey is null or
 * the content is not an E2EE payload (e.g. legacy plain-text messages).
 */
export async function decryptMessageContent(msg, sharedKey) {
  if (!msg?.content) return msg;

  // Try to detect an E2EE payload regardless of whether we have a key
  let parsed = null;
  try { parsed = JSON.parse(msg.content); } catch { return msg; }
  if (!parsed?.e2ee) return msg; // plain-text message — return as-is

  // We know it's encrypted. If we have no key yet, show a placeholder.
  if (!sharedKey) {
    return { ...msg, content: '🔒 [Encrypted — key exchange incomplete]' };
  }

  try {
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: new Uint8Array(b64ToBuf(parsed.iv)) },
      sharedKey,
      b64ToBuf(parsed.ciphertext),
    );
    return { ...msg, content: new TextDecoder().decode(decrypted) };
  } catch {
    return { ...msg, content: '🔒 [Encrypted — decryption failed]' };
  }
}
