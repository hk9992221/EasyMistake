const queues = new Map<string, Promise<unknown>>()

function ordered<T>(accountId: string, operation: () => Promise<T>): Promise<T> {
  const next = (queues.get(accountId) ?? Promise.resolve()).catch(() => undefined).then(operation)
  queues.set(accountId, next)
  const clean = () => { if (queues.get(accountId) === next) queues.delete(accountId) }
  void next.then(clean, clean)
  return next
}

function transact<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const opening = indexedDB.open('easymistake-drafts', 1)
    opening.onupgradeneeded = () => opening.result.createObjectStore('questions')
    opening.onerror = () => reject(opening.error)
    opening.onsuccess = () => {
      const db = opening.result
      const transaction = db.transaction('questions', mode)
      let result: T
      try {
        const request = action(transaction.objectStore('questions'))
        request.onsuccess = () => { result = request.result }
      } catch (error) {
        db.close()
        reject(error)
        return
      }
      transaction.oncomplete = () => { db.close(); resolve(result) }
      transaction.onabort = transaction.onerror = () => { db.close(); reject(transaction.error) }
    }
  })
}

export const questionDraft = {
  read: <T>(accountId: string) => ordered(accountId, () => transact<T | undefined>('readonly', (store) => store.get(accountId))),
  save: <T>(accountId: string, data: T) => ordered(accountId, () => transact('readwrite', (store) => store.put(data, accountId))),
  remove: (accountId: string) => ordered(accountId, () => transact('readwrite', (store) => store.delete(accountId))),
}
