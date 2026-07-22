export type TreeFile = {
  name: string;
  type: "file";
  path: string;
  language: string;
};

export type TreeDir = {
  name: string;
  type: "dir";
  children: (TreeFile | TreeDir)[];
};

export type TreeNode = TreeFile | TreeDir;

export type MCQ = {
  id: string;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
};

export type CodingTask = {
  type: "bug_fix" | "write_snippet";
  title: string;
  prompt: string;
  starter_code: string;
  reference_solution: string;
  explanation: string;
};

export type Quiz = {
  mcqs: MCQ[];
  coding_task: CodingTask;
  files_used: string[];
};

export type MCQResult = {
  id: string;
  selected_index: number | null;
  correct_index: number;
  is_correct: boolean;
  explanation: string;
};

export type CodingResult = {
  correct: boolean | null;
  feedback: string;
};

export type SubmitResponse = {
  attempt_id: number;
  mcq_results: MCQResult[];
  coding_result: CodingResult;
  score: number;
  max_score: number;
};

export type AttemptSummary = {
  id: number;
  repo_url: string;
  scope_path: string;
  created_at: string;
  score: number;
  max_score: number;
};
