import { initializeApp, type FirebaseApp } from 'firebase/app'
import {
  getFirestore, collection, addDoc, serverTimestamp, type Firestore,
} from 'firebase/firestore'

const config = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
}

// Firebase is optional during local dev — if config is missing, lead writes
// are no-ops and we just continue to the download.
let app: FirebaseApp | null = null
let db: Firestore | null = null
if (config.apiKey && config.projectId) {
  app = initializeApp(config)
  db = getFirestore(app)
}

export interface Lead {
  email: string
  propertyId: number
  appraisedValue?: number
  estimatedSavings?: number
  name?: string
  phone?: string
}

export async function captureLead(lead: Lead): Promise<void> {
  if (!db) {
    console.warn('Firestore not configured — skipping lead capture')
    return
  }
  await addDoc(collection(db, 'leads'), {
    ...lead,
    ts: serverTimestamp(),
    userAgent: navigator.userAgent,
    referrer: document.referrer || null,
  })
}
