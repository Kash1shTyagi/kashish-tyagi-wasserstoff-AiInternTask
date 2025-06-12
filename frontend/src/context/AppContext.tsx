import React, { createContext, useReducer, useContext, useEffect } from 'react';

export interface UploadBlobMap {
  [docId: string]: string; // blob URL
}

interface State {
  selectedDocIds: string[];
  blobMap: UploadBlobMap;
}

type Action =
  | { type: 'SET_SELECTED_DOCS'; payload: string[] }
  | { type: 'ADD_UPLOAD_RESULTS'; payload: { doc_id: string; previewUrl?: string }[] }
  | { type: 'HYDRATE_BLOBS'; payload: UploadBlobMap };

const initialState: State = {
  selectedDocIds: [],
  blobMap: {},
};

const AppContext = createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
} | null>(null);

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_SELECTED_DOCS':
      return { ...state, selectedDocIds: action.payload };
    case 'ADD_UPLOAD_RESULTS': {
      const newMap = { ...state.blobMap };
      action.payload.forEach(r => {
        if (r.previewUrl) newMap[r.doc_id] = r.previewUrl;
      });
      localStorage.setItem('blobMap', JSON.stringify(newMap));
      return { ...state, blobMap: newMap };
    }
    case 'HYDRATE_BLOBS':
      return { ...state, blobMap: action.payload };
    default:
      return state;
  }
}

export const AppContextProvider: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    const stored = localStorage.getItem('blobMap');
    if (stored) {
      try {
        dispatch({ type: 'HYDRATE_BLOBS', payload: JSON.parse(stored) });
      } catch {}
    }
  }, []);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
};

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used within AppContextProvider');
  return ctx;
}
