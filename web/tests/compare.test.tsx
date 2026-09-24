import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CompareView } from "@/components/CompareView";
import type { Category, PairDoc, Step } from "@/types/data";

const step = (index: number, action: Step["action"], file: string): Step => ({
  index, thought: `thinking about ${file}`, tool: "str_replace_editor", command: `${action} ${file}`,
  action, files: [file], output: `output of ${index}`, truncated: false, test_result: null,
});

const passSteps = [0, 1, 2, 3].map((i) => step(i, "view", `a${i}.py`)).concat([step(4, "edit", "a.py")]);
const failSteps = [0, 1, 2, 3].map((i) => step(i, "view", `a${i}.py`)).concat([step(4, "edit", "b.py")]);

const DOC: PairDoc = {
  pair_id: "p1", instance_id: "o__r.abc.pr_1", repo: "o/r", issue: "Crop fails",
  pass_run: { traj_id: "tp", model: "claude-3-7-sonnet-20250219", resolved: true, issue: "Crop fails", steps: passSteps, patch: "+fixed" },
  fail_run: { traj_id: "tf", model: "gpt-4o-2024-08-06", resolved: false, issue: "Crop fails", steps: failSteps, patch: "" },
  rows: [0, 1, 2, 3, 4].map((i) => ({ p: i, f: i, match: i < 4 })),
  candidates: [{ step: 4, rule: "foreign_edit" }],
  verdict: { split_step: 4, reason: "Edited b.py instead of a.py.", category: "wrong_location", confidence: 0.9 },
  validation: false,
};

const CATEGORIES: Category[] = [{ id: "wrong_location", label: "Wrong location", definition: "d" }];

describe("CompareView", () => {
  it("collapses matching steps and highlights the split with the judge's reason", () => {
    const { container } = render(<CompareView doc={DOC} categories={CATEGORIES} />);
    expect(screen.getByRole("button", { name: /Show 4 matching steps/ })).toBeInTheDocument();
    expect(container.querySelector('[data-tone="split"]')?.getAttribute("data-step")).toBe("4");
    expect(screen.getByTestId("judge-card")).toHaveTextContent("Split at step 4 of 5");
    expect(screen.getByTestId("judge-card")).toHaveTextContent("Wrong location");
  });

  it("expands a strip and a step", () => {
    render(<CompareView doc={DOC} categories={CATEGORIES} />);
    fireEvent.click(screen.getByRole("button", { name: /Show 4 matching steps/ }));
    expect(screen.getAllByText("a0.py")).toHaveLength(2);
    fireEvent.click(screen.getAllByText("a0.py")[1]);
    expect(screen.getByText("output of 0")).toBeInTheDocument();
  });

  it("hides the verdict and candidates in blind (label) mode", () => {
    const { container } = render(<CompareView doc={DOC} categories={CATEGORIES} blind />);
    expect(screen.queryByTestId("judge-card")).toBeNull();
    expect(screen.queryByText(/Edited b.py/)).toBeNull();
    expect(screen.queryByText(/Not judged yet/)).toBeNull();
    expect(container.querySelector('[data-tone="split"], [data-tone="candidate"]')).toBeNull();
  });

  it("shows alignment candidates when there is no verdict", () => {
    const { container } = render(<CompareView doc={{ ...DOC, verdict: null }} categories={CATEGORIES} />);
    expect(screen.getByText(/Not judged yet/)).toBeInTheDocument();
    expect(container.querySelector('[data-tone="candidate"]')?.getAttribute("data-step")).toBe("4");
  });
});
