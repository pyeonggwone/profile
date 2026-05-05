import { useEffect, useState } from "react";
import {
    downloadUrl,
    fetchPage,
    postEdits,
    uploadPdf,
    type EditOperation,
    type PageRenderPlan,
    type UploadResponse,
} from "./api";
import { PageCanvas } from "./components/PageCanvas";

type Tool = "select" | "text" | "note";

export default function App() {
    const [doc, setDoc] = useState<UploadResponse | null>(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [plan, setPlan] = useState<PageRenderPlan | null>(null);
    const [scale, setScale] = useState(1);
    const [tool, setTool] = useState<Tool>("select");
    const [pendingText, setPendingText] = useState("Sample text");
    const [pendingNote, setPendingNote] = useState("Note here");
    const [status, setStatus] = useState("PDF 파일을 업로드하세요.");
    const [pendingEdits, setPendingEdits] = useState<EditOperation[]>([]);

    // Load page render plan when doc / page changes.
    useEffect(() => {
        let alive = true;
        if (!doc) return;
        setPlan(null);
        fetchPage(doc.document.document_id, pageNumber)
            .then((p) => {
                if (alive) setPlan(p);
            })
            .catch((e: Error) => alive && setStatus(`페이지 로드 실패: ${e.message}`));
        return () => {
            alive = false;
        };
    }, [doc, pageNumber]);

    async function handleUpload(ev: React.ChangeEvent<HTMLInputElement>) {
        const file = ev.target.files?.[0];
        if (!file) return;
        setStatus(`업로드 중: ${file.name}`);
        try {
            const result = await uploadPdf(file);
            setDoc(result);
            setPageNumber(1);
            setPendingEdits([]);
            setStatus(
                `업로드 완료: ${result.summary.page_count} 페이지, PDF ${result.summary.pdf_version}`
            );
        } catch (e) {
            setStatus(`업로드 실패: ${(e as Error).message}`);
        }
    }

    async function handleSave() {
        if (!doc) return;
        if (pendingEdits.length === 0) {
            window.location.href = downloadUrl(doc.document.document_id);
            return;
        }
        try {
            await postEdits(doc.document.document_id, pendingEdits);
            setPendingEdits([]);
            setStatus("편집 저장 완료. 다운로드를 시작합니다.");
            window.location.href = downloadUrl(doc.document.document_id);
        } catch (e) {
            setStatus(`저장 실패: ${(e as Error).message}`);
        }
    }

    function handleCanvasClick(xPdf: number, yPdf: number) {
        if (!doc) return;
        if (tool === "text") {
            const op: EditOperation = {
                type: "AddText",
                page: pageNumber,
                x: xPdf,
                y: yPdf,
                text: pendingText,
                font: "Helvetica",
                size: 12,
                color: [0, 0, 0],
            };
            setPendingEdits((e) => [...e, op]);
            setStatus(`텍스트 추가 위치: (${xPdf.toFixed(1)}, ${yPdf.toFixed(1)})`);
        } else if (tool === "note") {
            const op: EditOperation = {
                type: "AddTextAnnotation",
                page: pageNumber,
                x: xPdf,
                y: yPdf,
                contents: pendingNote,
            };
            setPendingEdits((e) => [...e, op]);
            setStatus(`주석 추가 위치: (${xPdf.toFixed(1)}, ${yPdf.toFixed(1)})`);
        }
    }

    return (
        <div className="app">
            <div className="toolbar">
                <label>
                    <input
                        type="file"
                        accept="application/pdf"
                        onChange={handleUpload}
                        style={{ display: "none" }}
                    />
                    <span
                        style={{
                            background: "#3a3d42",
                            padding: "6px 12px",
                            borderRadius: 4,
                            cursor: "pointer",
                            border: "1px solid #4d5057",
                            fontSize: 13,
                        }}
                    >
                        PDF 업로드
                    </span>
                </label>
                <button disabled={!doc} onClick={() => setTool("select")} aria-pressed={tool === "select"}>
                    선택
                </button>
                <button disabled={!doc} onClick={() => setTool("text")} aria-pressed={tool === "text"}>
                    텍스트
                </button>
                <button disabled={!doc} onClick={() => setTool("note")} aria-pressed={tool === "note"}>
                    주석
                </button>
                <span className="spacer" />
                <button disabled={!doc} onClick={() => setScale((s) => Math.max(0.25, s - 0.25))}>
                    축소
                </button>
                <span style={{ minWidth: 48, textAlign: "center" }}>
                    {Math.round(scale * 100)}%
                </span>
                <button disabled={!doc} onClick={() => setScale((s) => Math.min(4, s + 0.25))}>
                    확대
                </button>
                <button disabled={!doc} onClick={handleSave}>
                    저장 / 다운로드
                </button>
            </div>

            <div className="workspace">
                <aside className="panel">
                    {doc ? (
                        doc.summary.pages.map((p) => (
                            <button
                                key={p.page}
                                className={`thumb ${p.page === pageNumber ? "active" : ""}`}
                                onClick={() => setPageNumber(p.page)}
                            >
                                페이지 {p.page}
                                <br />
                                <span style={{ color: "#888" }}>
                                    {Math.round(p.width)} × {Math.round(p.height)}
                                </span>
                            </button>
                        ))
                    ) : (
                        <div style={{ color: "#888", fontSize: 13 }}>아직 문서가 없습니다.</div>
                    )}
                </aside>

                <main className="canvas-area">
                    {plan ? (
                        <PageCanvas
                            plan={plan}
                            scale={scale}
                            onClick={tool === "select" ? undefined : handleCanvasClick}
                        />
                    ) : doc ? (
                        <div style={{ color: "#888" }}>페이지 로드 중...</div>
                    ) : (
                        <div style={{ color: "#888" }}>파일을 업로드하세요.</div>
                    )}
                </main>

                <aside className="panel panel-right">
                    {tool === "text" && (
                        <div>
                            <h3>텍스트 도구</h3>
                            <div className="field">
                                <label>내용</label>
                                <input
                                    value={pendingText}
                                    onChange={(e) => setPendingText(e.target.value)}
                                />
                            </div>
                            <div style={{ fontSize: 12, color: "#888" }}>
                                캔버스를 클릭해 위치를 지정합니다.
                            </div>
                        </div>
                    )}
                    {tool === "note" && (
                        <div>
                            <h3>주석 도구</h3>
                            <div className="field">
                                <label>주석 내용</label>
                                <textarea
                                    rows={4}
                                    value={pendingNote}
                                    onChange={(e) => setPendingNote(e.target.value)}
                                />
                            </div>
                        </div>
                    )}
                    <hr style={{ borderColor: "#3a3d42" }} />
                    <h4>대기 중인 편집 ({pendingEdits.length})</h4>
                    <ul style={{ paddingLeft: 16, fontSize: 12 }}>
                        {pendingEdits.map((op, i) => (
                            <li key={i}>
                                {op.type === "AddText"
                                    ? `Text "${op.text}" @ p${op.page}`
                                    : `Note "${op.contents}" @ p${op.page}`}
                            </li>
                        ))}
                    </ul>
                    {doc && (
                        <>
                            <hr style={{ borderColor: "#3a3d42" }} />
                            <h4>문서 정보</h4>
                            <div style={{ fontSize: 12 }}>
                                <div>버전: {doc.summary.pdf_version}</div>
                                <div>페이지: {doc.summary.page_count}</div>
                                {doc.summary.title && <div>제목: {doc.summary.title}</div>}
                                {doc.summary.author && <div>저자: {doc.summary.author}</div>}
                            </div>
                        </>
                    )}
                </aside>
            </div>

            <div className="status-bar">{status}</div>
        </div>
    );
}
