import { initializeApp } from 'firebase/app'
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type Auth,
  type Unsubscribe,
  type User,
} from 'firebase/auth'
import {
  addDoc,
  collection,
  getDocs,
  getFirestore,
  limit,
  orderBy,
  query,
  serverTimestamp,
  Timestamp,
  type Firestore,
} from 'firebase/firestore'

export const ADMIN_EMAIL = 'albertosilva@silvaconsultinggroup.com'

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

let db: Firestore | null = null
let auth: Auth | null = null
if (config.apiKey && config.projectId) {
  const app = initializeApp(config)
  db = getFirestore(app)
  auth = getAuth(app)
}

export interface Lead {
  email: string
  county: string
  countyLabel?: string
  propertyId: string
  situsAddress?: string
  owner?: string
  appraisedValue?: number
  targetValue?: number
  estimatedReduction?: number
  estimatedSavings?: number
  isProtestable?: boolean
  requestType?: 'packet' | 'info'
  reason?: string
  name?: string
  phone?: string
}

export interface AdminLead extends Lead {
  id: string
  createdAt?: string
}

export async function captureLead(lead: Lead): Promise<void> {
  if (!db) {
    console.warn('Firestore not configured - skipping lead capture')
    return
  }
  await addDoc(collection(db, 'leads'), {
    ...withoutUndefined(lead),
    ts: serverTimestamp(),
    userAgent: navigator.userAgent,
    referrer: document.referrer || null,
  })
}

export function isFirebaseConfigured(): boolean {
  return Boolean(auth && db)
}

export function isAdminUser(user: User | null): boolean {
  return user?.email?.toLowerCase() === ADMIN_EMAIL
}

export function subscribeToAuth(callback: (user: User | null) => void): Unsubscribe {
  if (!auth) {
    callback(null)
    return () => undefined
  }
  return onAuthStateChanged(auth, callback)
}

export async function signInAdmin(email: string, password: string): Promise<void> {
  if (!auth) throw new Error('Firebase Auth is not configured')
  await signInWithEmailAndPassword(auth, email, password)
}

export async function signOutAdmin(): Promise<void> {
  if (!auth) return
  await signOut(auth)
}

export async function listLeads(maxLeads = 100): Promise<AdminLead[]> {
  if (!db) throw new Error('Firestore is not configured')

  const snapshot = await getDocs(
    query(collection(db, 'leads'), orderBy('ts', 'desc'), limit(maxLeads)),
  )

  return snapshot.docs.map((doc) => {
    const data = doc.data() as Record<string, unknown>
    return {
      id: doc.id,
      email: stringValue(data.email),
      county: optionalString(data.county) ?? 'bexar',
      countyLabel: optionalString(data.countyLabel),
      propertyId: idValue(data.propertyId),
      situsAddress: optionalString(data.situsAddress),
      owner: optionalString(data.owner),
      appraisedValue: optionalNumber(data.appraisedValue),
      targetValue: optionalNumber(data.targetValue),
      estimatedReduction: optionalNumber(data.estimatedReduction),
      estimatedSavings: optionalNumber(data.estimatedSavings),
      isProtestable: optionalBoolean(data.isProtestable),
      requestType: data.requestType === 'packet' ? 'packet' : 'info',
      reason: optionalString(data.reason),
      name: optionalString(data.name),
      phone: optionalString(data.phone),
      createdAt: timestampLabel(data.ts),
    }
  })
}

function stringValue(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function idValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number') return String(value)
  return ''
}

function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' ? value : undefined
}

function optionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined
}

function optionalBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined
}

function timestampLabel(value: unknown): string | undefined {
  if (value instanceof Timestamp) {
    return value.toDate().toLocaleString()
  }
  return undefined
}

function withoutUndefined<T extends object>(input: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(input).filter(([, value]) => value !== undefined),
  ) as Partial<T>
}
