// Server contract types (match the Rust side under crates/server).

export interface DocumentMeta {
    document_id: string;
    original_filename: string;
    size_bytes: number;
    uploaded_at: string;
    pdf_version: string;
    page_count: number;
    encrypted: boolean;
}

export interface PageSummary {
    page: number;
    width: number;
    height: number;
    rotate: number;
}

export interface DocumentSummary {
    pdf_version: string;
    page_count: number;
    title: string | null;
    author: string | null;
    subject: string | null;
    creator: string | null;
    producer: string | null;
    encrypted: boolean;
    pages: PageSummary[];
    warnings: string[];
}

export interface UploadResponse {
    document: DocumentMeta;
    summary: DocumentSummary;
}

export type RenderCommand =
    | {
        op: "text";
        text: string;
        x: number;
        y: number;
        fontSize: number;
        fontResource: string | null;
    };

export interface PageRenderPlan {
    page: number;
    width: number;
    height: number;
    commands: RenderCommand[];
}

export type EditOperation =
    | {
        type: "AddText";
        page: number;
        x: number;
        y: number;
        text: string;
        font: "Helvetica" | "HelveticaBold" | "TimesRoman" | "Courier";
        size: number;
        color: [number, number, number];
    }
    | {
        type: "AddTextAnnotation";
        page: number;
        x: number;
        y: number;
        contents: string;
    };

const BASE = ""; // proxy via vite

export async function uploadPdf(file: File): Promise<UploadResponse> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/documents`, {
        method: "POST",
        body: form,
    });
    if (!res.ok) throw await asError(res);
    return res.json();
}

export async function fetchPage(
    documentId: string,
    page: number
): Promise<PageRenderPlan> {
    const res = await fetch(
        `${BASE}/api/documents/${documentId}/pages/${page}`
    );
    if (!res.ok) throw await asError(res);
    return res.json();
}

export async function postEdits(
    documentId: string,
    operations: EditOperation[]
): Promise<void> {
    const res = await fetch(
        `${BASE}/api/documents/${documentId}/edits`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operations }),
        }
    );
    if (!res.ok) throw await asError(res);
}

export function downloadUrl(documentId: string): string {
    return `${BASE}/api/documents/${documentId}/download`;
}

async function asError(res: Response): Promise<Error> {
    try {
        const body = await res.json();
        return new Error(`${body.code ?? res.status}: ${body.message ?? res.statusText}`);
    } catch {
        return new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
}
