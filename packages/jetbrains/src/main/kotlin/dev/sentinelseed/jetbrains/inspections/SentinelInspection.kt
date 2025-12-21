package dev.sentinelseed.jetbrains.inspections

import com.intellij.codeInspection.*
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiElementVisitor
import com.intellij.psi.PsiFile
import com.intellij.psi.PsiPlainText
import dev.sentinelseed.jetbrains.settings.SentinelApplicationSettings

/**
 * Code inspection that checks for unsafe patterns in real-time
 * Uses heuristic pattern matching for speed
 */
class SentinelInspection : LocalInspectionTool() {

    companion object {
        // Pattern definitions for quick heuristic checks
        private val TRUTH_PATTERNS = listOf(
            "ignore previous" to "Attempts to override previous instructions",
            "pretend you are" to "Identity manipulation attempt",
            "act as if" to "Context manipulation attempt",
            "forget your" to "Memory manipulation attempt",
            "disregard" to "Instruction override attempt",
            "new persona" to "Identity change attempt"
        )

        private val HARM_PATTERNS = listOf(
            "how to hack" to "Potential security attack guidance",
            "bypass security" to "Security bypass attempt",
            "steal" to "Theft-related content",
            "exploit vulnerability" to "Exploitation guidance",
            "malware" to "Malicious software reference",
            "ransomware" to "Ransomware reference",
            "phishing" to "Phishing attack"
        )

        private val SCOPE_PATTERNS = listOf(
            "jailbreak" to "Jailbreak attempt",
            "unlock restrictions" to "Restriction bypass attempt",
            "remove safety" to "Safety removal attempt",
            "disable filter" to "Filter bypass attempt",
            "no limits" to "Limit removal attempt",
            "unrestricted mode" to "Mode bypass attempt"
        )

        private val PURPOSE_PATTERNS = listOf(
            "for fun" to "No legitimate purpose stated",
            "just because" to "No clear intent",
            "i want to hurt" to "Malicious intent",
            "destroy" to "Destructive intent"
        )
    }

    override fun getGroupDisplayName(): String = "Sentinel AI Safety"

    override fun getShortName(): String = "SentinelSafetyInspection"

    override fun isEnabledByDefault(): Boolean = true

    override fun buildVisitor(holder: ProblemsHolder, isOnTheFly: Boolean): PsiElementVisitor {
        val settings = SentinelApplicationSettings.getInstance()

        if (!settings.enableRealTimeLinting || !settings.highlightUnsafePatterns) {
            return PsiElementVisitor.EMPTY_VISITOR
        }

        return object : PsiElementVisitor() {
            override fun visitFile(file: PsiFile) {
                // Only inspect supported file types
                val supportedExtensions = listOf("md", "txt", "py", "js", "ts", "json", "yaml", "yml")
                val extension = file.virtualFile?.extension?.lowercase() ?: return

                if (extension !in supportedExtensions) return

                val text = file.text.lowercase()

                // Check each pattern category
                checkPatterns(file, text, TRUTH_PATTERNS, "Truth Gate", holder)
                checkPatterns(file, text, HARM_PATTERNS, "Harm Gate", holder)
                checkPatterns(file, text, SCOPE_PATTERNS, "Scope Gate", holder)
                checkPatterns(file, text, PURPOSE_PATTERNS, "Purpose Gate", holder)
            }
        }
    }

    private fun checkPatterns(
        file: PsiFile,
        text: String,
        patterns: List<Pair<String, String>>,
        gateName: String,
        holder: ProblemsHolder
    ) {
        for ((pattern, description) in patterns) {
            var startIndex = 0
            while (true) {
                val index = text.indexOf(pattern, startIndex)
                if (index == -1) break

                // Find the element at this position
                val element = file.findElementAt(index)
                if (element != null) {
                    holder.registerProblem(
                        element,
                        "Sentinel: $gateName violation - $description",
                        ProblemHighlightType.WARNING,
                        SentinelQuickFix()
                    )
                }

                startIndex = index + pattern.length
            }
        }
    }
}

/**
 * Quick fix to analyze with full semantic validation
 */
class SentinelQuickFix : LocalQuickFix {
    override fun getName(): String = "Analyze with Sentinel"

    override fun getFamilyName(): String = "Sentinel AI Safety"

    override fun applyFix(project: Project, descriptor: ProblemDescriptor) {
        // Open Sentinel tool window and suggest full analysis
        val toolWindow = com.intellij.openapi.wm.ToolWindowManager.getInstance(project)
            .getToolWindow("Sentinel")
        toolWindow?.show {
            dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory.showMessage(
                project,
                "Select the text and use Ctrl+Shift+Alt+S for full semantic analysis",
                isError = false
            )
        }
    }
}
