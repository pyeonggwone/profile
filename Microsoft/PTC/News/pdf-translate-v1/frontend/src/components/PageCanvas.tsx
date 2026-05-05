import { useEffect, useRef } from "react";
import type { PageRenderPlan } from "../api";

interface Props {
    plan: PageRenderPlan;
    scale: number;
    onClick?: (xPdf: number, yPdf: number) => void;
}

/**
 * PageCanvas
 *
 * Renders a PageRenderPlan to a Canvas 2D layer. The browser does not
 * decode any PDF content — every drawing instruction comes from the
 * server-side render plan.
 */
export function PageCanvas({ plan, scale, onClick }: Props) {
    const ref = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = ref.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const w = plan.width * scale;
        const h = plan.height * scale;
        canvas.width = w;
        canvas.height = h;
        canvas.style.width = `${w}px`;
        canvas.style.height = `${h}px`;
        ctx.fillStyle = "white";
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = "#111";
        ctx.textBaseline = "alphabetic";
        for (const cmd of plan.commands) {
            if (cmd.op === "text") {
                ctx.font = `${cmd.fontSize * scale}px sans-serif`;
                ctx.fillText(cmd.text, cmd.x * scale, cmd.y * scale);
            }
        }
    }, [plan, scale]);

    function handleClick(ev: React.MouseEvent<HTMLCanvasElement>) {
        if (!onClick) return;
        const rect = ev.currentTarget.getBoundingClientRect();
        const x = (ev.clientX - rect.left) / scale;
        const y = (ev.clientY - rect.top) / scale;
        onClick(x, y);
    }

    return (
        <canvas
            ref={ref}
            className="page-canvas"
            onClick={handleClick}
        />
    );
}
