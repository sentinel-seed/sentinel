package dev.sentinelseed.jetbrains.ui

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.openapi.wm.ToolWindowManager
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.content.ContentFactory
import dev.sentinelseed.jetbrains.services.AnalysisMethod
import dev.sentinelseed.jetbrains.services.AnalysisResult
import dev.sentinelseed.jetbrains.services.GateStatus
import java.awt.BorderLayout
import java.awt.Color
import java.awt.Font
import javax.swing.*

/**
 * Factory for creating the Sentinel tool window
 */
class SentinelToolWindowFactory : ToolWindowFactory, DumbAware {

    companion object {
        private val panels = mutableMapOf<Project, SentinelPanel>()

        fun showResult(project: Project, result: AnalysisResult) {
            ApplicationManager.getApplication().invokeLater {
                val toolWindow = ToolWindowManager.getInstance(project).getToolWindow("Sentinel")
                toolWindow?.show {
                    panels[project]?.showResult(result)
                }
            }
        }

        fun showMessage(project: Project, message: String, isError: Boolean = false) {
            ApplicationManager.getApplication().invokeLater {
                val toolWindow = ToolWindowManager.getInstance(project).getToolWindow("Sentinel")
                toolWindow?.show {
                    panels[project]?.showMessage(message, isError)
                }
            }
        }
    }

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val panel = SentinelPanel()
        panels[project] = panel

        val content = ContentFactory.getInstance().createContent(panel, "", false)
        toolWindow.contentManager.addContent(content)
    }

    override fun shouldBeAvailable(project: Project): Boolean = true
}

/**
 * Panel for displaying analysis results
 */
class SentinelPanel : JPanel(BorderLayout()) {

    private val resultPanel = JPanel()
    private val scrollPane = JBScrollPane(resultPanel)

    init {
        resultPanel.layout = BoxLayout(resultPanel, BoxLayout.Y_AXIS)
        resultPanel.border = BorderFactory.createEmptyBorder(10, 10, 10, 10)

        add(scrollPane, BorderLayout.CENTER)
        showWelcome()
    }

    private fun showWelcome() {
        resultPanel.removeAll()

        val welcomeLabel = JBLabel("<html><b>Sentinel AI Safety</b></html>")
        welcomeLabel.font = welcomeLabel.font.deriveFont(Font.BOLD, 14f)

        val infoLabel = JBLabel("<html>" +
                "Select text and use <b>Ctrl+Shift+Alt+S</b> to analyze,<br/>" +
                "or right-click and select <b>Sentinel → Analyze Selection</b>.<br/><br/>" +
                "Configure API keys in <b>Settings → Tools → Sentinel AI Safety</b><br/>" +
                "for semantic analysis (~90% accuracy)." +
                "</html>")

        resultPanel.add(welcomeLabel)
        resultPanel.add(Box.createVerticalStrut(10))
        resultPanel.add(infoLabel)

        revalidate()
        repaint()
    }

    fun showResult(result: AnalysisResult) {
        resultPanel.removeAll()

        // Status header
        val statusIcon = if (result.safe) "✅" else "⚠️"
        val statusText = if (result.safe) "SAFE" else "UNSAFE"
        val statusColor = if (result.safe) Color(46, 125, 50) else Color(198, 40, 40)

        val statusLabel = JBLabel("<html><b>$statusIcon $statusText</b></html>")
        statusLabel.font = statusLabel.font.deriveFont(Font.BOLD, 16f)
        statusLabel.foreground = statusColor
        resultPanel.add(statusLabel)
        resultPanel.add(Box.createVerticalStrut(15))

        // Analysis method
        val methodIcon = if (result.method == AnalysisMethod.SEMANTIC) "🧠" else "📋"
        val methodText = if (result.method == AnalysisMethod.SEMANTIC) "Semantic" else "Heuristic"
        val confidence = (result.confidence * 100).toInt()

        val methodLabel = JBLabel("<html><b>Analysis:</b> $methodIcon $methodText ($confidence% confidence)</html>")
        resultPanel.add(methodLabel)
        resultPanel.add(Box.createVerticalStrut(15))

        // Gates
        val gatesLabel = JBLabel("<html><b>Gates:</b></html>")
        gatesLabel.font = gatesLabel.font.deriveFont(Font.BOLD)
        resultPanel.add(gatesLabel)
        resultPanel.add(Box.createVerticalStrut(5))

        addGateRow("Truth", result.gates.truth)
        addGateRow("Harm", result.gates.harm)
        addGateRow("Scope", result.gates.scope)
        addGateRow("Purpose", result.gates.purpose)

        // Issues
        if (result.issues.isNotEmpty()) {
            resultPanel.add(Box.createVerticalStrut(15))
            val issuesLabel = JBLabel("<html><b>Issues:</b></html>")
            issuesLabel.font = issuesLabel.font.deriveFont(Font.BOLD)
            resultPanel.add(issuesLabel)
            resultPanel.add(Box.createVerticalStrut(5))

            for (issue in result.issues) {
                val issueLabel = JBLabel("• $issue")
                issueLabel.foreground = Color(198, 40, 40)
                resultPanel.add(issueLabel)
            }
        }

        // Reasoning
        if (!result.reasoning.isNullOrBlank()) {
            resultPanel.add(Box.createVerticalStrut(15))
            val reasoningLabel = JBLabel("<html><b>Reasoning:</b></html>")
            reasoningLabel.font = reasoningLabel.font.deriveFont(Font.BOLD)
            resultPanel.add(reasoningLabel)
            resultPanel.add(Box.createVerticalStrut(5))

            val reasoningText = JBLabel("<html>${result.reasoning}</html>")
            reasoningText.foreground = Color.GRAY
            resultPanel.add(reasoningText)
        }

        // Heuristic warning
        if (result.method == AnalysisMethod.HEURISTIC) {
            resultPanel.add(Box.createVerticalStrut(15))
            val warningLabel = JBLabel("<html><i>⚠️ For accurate semantic analysis, " +
                    "configure an LLM API key in settings.</i></html>")
            warningLabel.foreground = Color(255, 152, 0)
            resultPanel.add(warningLabel)
        }

        resultPanel.add(Box.createVerticalGlue())
        revalidate()
        repaint()
    }

    private fun addGateRow(name: String, status: GateStatus) {
        val icon = if (status == GateStatus.PASS) "✓" else "✗"
        val color = if (status == GateStatus.PASS) Color(46, 125, 50) else Color(198, 40, 40)
        val statusText = if (status == GateStatus.PASS) "pass" else "fail"

        val label = JBLabel("  $icon $name: $statusText")
        label.foreground = color
        resultPanel.add(label)
    }

    fun showMessage(message: String, isError: Boolean) {
        resultPanel.removeAll()

        val icon = if (isError) "❌" else "ℹ️"
        val color = if (isError) Color(198, 40, 40) else Color.GRAY

        val label = JBLabel("<html>$icon $message</html>")
        label.foreground = color
        resultPanel.add(label)

        revalidate()
        repaint()
    }
}
