# ElasticBurp
# Copyright 2016 Thomas Patzke <thomas@patzke.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from burp import (
    IBurpExtender,
    IBurpExtenderCallbacks,
    IHttpListener,
    IRequestInfo,
    IParameter,
    IContextMenuFactory,
    ITab,
)
from javax.swing import (
    JMenuItem,
    ProgressMonitor,
    JPanel,
    BoxLayout,
    JLabel,
    JTextField,
    JCheckBox,
    JButton,
    Box,
    JOptionPane,
    GroupLayout,
)
from javax.swing.border import EmptyBorder
from java.awt import Dimension
from elasticsearch7_dsl.connections import connections
from elasticsearch7_dsl import Index
from elasticsearch7.helpers import bulk
from lib.doc_HttpRequestResponse import DocHTTPRequestResponse
from lib.threadpool import TaskExecutor
from datetime import datetime
from email.utils import parsedate_tz, mktime_tz
from tzlocal import get_localzone
import re

try:
    tz = get_localzone()
except:
    tz = None
reDateHeader = re.compile("^Date:\s*(.*)$", flags=re.IGNORECASE)

### Config (TODO: move to config tab) ###
ES_host = "localhost"
ES_index = "wase-burp"
Burp_Tools = IBurpExtenderCallbacks.TOOL_PROXY
Burp_onlyResponses = True  # Usually what you want, responses also contain requests
#########################################


class BurpExtender(IBurpExtender, IHttpListener, IContextMenuFactory, ITab):
    def registerExtenderCallbacks(self, callbacks):
        self.callbacks = callbacks
        self.helpers = callbacks.getHelpers()
        callbacks.setExtensionName("ElasticBurp")
        callbacks.registerHttpListener(self)
        callbacks.registerContextMenuFactory(self)
        self.out = callbacks.getStdout()

        self.lastTimestamp = None
        self.confESHost = callbacks.loadExtensionSetting("elasticburp.host") or ES_host
        self.confESIndex = (
            callbacks.loadExtensionSetting("elasticburp.index") or ES_index
        )
        self.confBurpTools = int(
            callbacks.loadExtensionSetting("elasticburp.tools") or Burp_Tools
        )
        saved_onlyresp = self.callbacks.loadExtensionSetting("elasticburp.onlyresp")
        if saved_onlyresp == "True":
            self.confBurpOnlyResp = True
        elif saved_onlyresp == "False":
            self.confBurpOnlyResp = False
        else:
            self.confBurpOnlyResp = bool(int(saved_onlyresp or Burp_onlyResponses))

        callbacks.addSuiteTab(self)
        self.applyConfig()
        self.executor = TaskExecutor(maxThreads=64)

    def applyConfig(self):
        try:
            print(
                "Connecting to '%s', index '%s'" % (self.confESHost, self.confESIndex)
            )
            self.es = connections.create_connection(hosts=[self.confESHost])
            self.idx = Index(self.confESIndex)
            self.idx.document(DocHTTPRequestResponse)
            if self.idx.exists():
                self.idx.open()
            else:
                self.idx.create()
            self.callbacks.saveExtensionSetting("elasticburp.host", self.confESHost)
            self.callbacks.saveExtensionSetting("elasticburp.index", self.confESIndex)
            self.callbacks.saveExtensionSetting(
                "elasticburp.tools", str(self.confBurpTools)
            )
            self.callbacks.saveExtensionSetting(
                "elasticburp.onlyresp", str(int(self.confBurpOnlyResp))
            )
        except Exception as e:
            JOptionPane.showMessageDialog(
                self.panel,
                "<html><p style='width: 300px'>Error while initializing ElasticSearch: %s</p></html>"
                % (str(e)),
                "Error",
                JOptionPane.ERROR_MESSAGE,
            )

    ### ITab ###
    def getTabCaption(self):
        return "ElasticBurp"

    def applyConfigUI(self, event):
        # self.idx.close()
        self.confESHost = self.uiESHost.getText()
        self.confESIndex = self.uiESIndex.getText()
        self.confBurpTools = int(
            (self.uiCBSuite.isSelected() and IBurpExtenderCallbacks.TOOL_SUITE)
            | (self.uiCBTarget.isSelected() and IBurpExtenderCallbacks.TOOL_TARGET)
            | (self.uiCBProxy.isSelected() and IBurpExtenderCallbacks.TOOL_PROXY)
            | (self.uiCBSpider.isSelected() and IBurpExtenderCallbacks.TOOL_SPIDER)
            | (self.uiCBScanner.isSelected() and IBurpExtenderCallbacks.TOOL_SCANNER)
            | (self.uiCBIntruder.isSelected() and IBurpExtenderCallbacks.TOOL_INTRUDER)
            | (self.uiCBRepeater.isSelected() and IBurpExtenderCallbacks.TOOL_REPEATER)
            | (
                self.uiCBSequencer.isSelected()
                and IBurpExtenderCallbacks.TOOL_SEQUENCER
            )
            | (self.uiCBExtender.isSelected() and IBurpExtenderCallbacks.TOOL_EXTENDER)
        )
        self.confBurpOnlyResp = self.uiCBOptRespOnly.isSelected()
        self.applyConfig()

    def resetConfigUI(self, event):
        self.uiESHost.setText(self.confESHost)
        self.uiESIndex.setText(self.confESIndex)
        self.uiCBSuite.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_SUITE)
        )
        self.uiCBTarget.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_TARGET)
        )
        self.uiCBProxy.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_PROXY)
        )
        self.uiCBSpider.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_SPIDER)
        )
        self.uiCBScanner.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_SCANNER)
        )
        self.uiCBIntruder.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_INTRUDER)
        )
        self.uiCBRepeater.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_REPEATER)
        )
        self.uiCBSequencer.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_SEQUENCER)
        )
        self.uiCBExtender.setSelected(
            bool(self.confBurpTools & IBurpExtenderCallbacks.TOOL_EXTENDER)
        )
        self.uiCBOptRespOnly.setSelected(self.confBurpOnlyResp)

    def getUiComponent(self):
        self.panel = JPanel()
        self.panel.setBorder(EmptyBorder(10, 10, 10, 10))
        self.panel.setLayout(BoxLayout(self.panel, BoxLayout.PAGE_AXIS))

        uiTextBoxPanel = JPanel()
        uiTextBoxPanel.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        uiTextBoxLayout = GroupLayout(uiTextBoxPanel)
        uiTextBoxPanel.setLayout(uiTextBoxLayout)
        uiTextBoxLayout.setAutoCreateGaps(True)
        uiTextBoxLayout.setAutoCreateContainerGaps(True)
        uiEsHostLabel = JLabel("ElasticSearch host: ")
        self.uiESHost = JTextField(20)
        self.uiESHost.setMaximumSize(self.uiESHost.getPreferredSize())
        uiEsIndexLabel = JLabel("ElasticSearch index: ")
        self.uiESIndex = JTextField(20)
        self.uiESIndex.setMaximumSize(self.uiESIndex.getPreferredSize())
        uiTextBoxHGroup = uiTextBoxLayout.createSequentialGroup()
        uiTextBoxHGroup.addGroup(
            uiTextBoxLayout.createParallelGroup()
            .addComponent(uiEsHostLabel)
            .addComponent(uiEsIndexLabel)
        )
        uiTextBoxHGroup.addGroup(
            uiTextBoxLayout.createParallelGroup()
            .addComponent(self.uiESHost)
            .addComponent(self.uiESIndex)
        )
        uiTextBoxLayout.setHorizontalGroup(uiTextBoxHGroup)
        uiTextBoxVGroup = uiTextBoxLayout.createSequentialGroup()
        uiTextBoxVGroup.addGroup(
            uiTextBoxLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
            .addComponent(uiEsHostLabel)
            .addComponent(self.uiESHost)
        )
        uiTextBoxVGroup.addGroup(
            uiTextBoxLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
            .addComponent(uiEsIndexLabel)
            .addComponent(self.uiESIndex)
        )
        uiTextBoxLayout.setVerticalGroup(uiTextBoxVGroup)
        self.panel.add(uiTextBoxPanel)

        self.uiCBSuite = JCheckBox("Suite")
        self.uiCBTarget = JCheckBox("Target")
        self.uiCBProxy = JCheckBox("Proxy")
        self.uiCBSpider = JCheckBox("Spider")
        self.uiCBScanner = JCheckBox("Scanner")
        self.uiCBIntruder = JCheckBox("Intruder")
        self.uiCBRepeater = JCheckBox("Repeater")
        self.uiCBSequencer = JCheckBox("Sequencer")
        self.uiCBExtender = JCheckBox("Extender")

        uiToolsPanel = JPanel()
        uiToolsPanel.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        uiToolsLayout = GroupLayout(uiToolsPanel)
        uiToolsPanel.setLayout(uiToolsLayout)
        uiToolsLayout.setAutoCreateGaps(True)
        uiToolsLayout.setAutoCreateContainerGaps(True)
        self.uiESHost.setMaximumSize(self.uiESHost.getPreferredSize())
        self.uiESIndex.setMaximumSize(self.uiESIndex.getPreferredSize())
        uiToolsHGroup = uiToolsLayout.createSequentialGroup()
        uiToolsHGroup.addGroup(
            uiToolsLayout.createParallelGroup()
            .addComponent(self.uiCBProxy)
            .addComponent(self.uiCBIntruder)
        )
        uiToolsHGroup.addGroup(
            uiToolsLayout.createParallelGroup()
            .addComponent(self.uiCBScanner)
            .addComponent(self.uiCBSequencer)
        )
        uiToolsHGroup.addGroup(
            uiToolsLayout.createParallelGroup()
            .addComponent(self.uiCBRepeater)
            .addComponent(self.uiCBExtender)
        )
        uiToolsLayout.setHorizontalGroup(uiToolsHGroup)
        uiToolsVGroup = uiToolsLayout.createSequentialGroup()
        uiToolsVGroup.addGroup(
            uiToolsLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
            .addComponent(self.uiCBProxy)
            .addComponent(self.uiCBScanner)
            .addComponent(self.uiCBRepeater)
        )
        uiToolsVGroup.addGroup(
            uiToolsLayout.createParallelGroup(GroupLayout.Alignment.BASELINE)
            .addComponent(self.uiCBIntruder)
            .addComponent(self.uiCBSequencer)
            .addComponent(self.uiCBExtender)
        )
        uiToolsLayout.setVerticalGroup(uiToolsVGroup)
        self.panel.add(uiToolsPanel)

        uiOptionsLine = JPanel()
        uiOptionsLine.setBorder(EmptyBorder(2, 2, 2, 2))
        uiOptionsLine.setLayout(BoxLayout(uiOptionsLine, BoxLayout.LINE_AXIS))
        uiOptionsLine.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        self.uiCBOptRespOnly = JCheckBox("Process only responses (includes requests)")
        uiOptionsLine.add(self.uiCBOptRespOnly)
        self.panel.add(uiOptionsLine)
        self.panel.add(Box.createRigidArea(Dimension(0, 10)))

        uiButtonsLine = JPanel()
        uiButtonsLine.setBorder(EmptyBorder(2, 2, 2, 2))
        uiButtonsLine.setLayout(BoxLayout(uiButtonsLine, BoxLayout.LINE_AXIS))
        uiButtonsLine.setAlignmentX(JPanel.LEFT_ALIGNMENT)
        uiButtonsLine.add(JButton("Apply", actionPerformed=self.applyConfigUI))
        uiButtonsLine.add(Box.createRigidArea(Dimension(10, 0)))
        uiButtonsLine.add(JButton("Reset", actionPerformed=self.resetConfigUI))
        self.panel.add(uiButtonsLine)
        self.resetConfigUI(None)

        return self.panel

    ### IHttpListener ###
    def __processHttpMessage(self, tool, isRequest, msg):
        if not tool & self.confBurpTools or isRequest and self.confBurpOnlyResp:
            return

        doc = self.genESDoc(msg)
        doc.save()

    def processHttpMessage(self, tool, isRequest, msg):
        self.executor.runBackground(self.__processHttpMessage, tool, isRequest, msg)

    ### IContextMenuFactory ###
    def createMenuItems(self, invocation):
        menuItems = list()
        selectedMsgs = invocation.getSelectedMessages()
        if selectedMsgs != None and len(selectedMsgs) >= 1:
            menuItems.append(
                JMenuItem(
                    "Add to ElasticSearch Index",
                    actionPerformed=self.genAddToES(
                        selectedMsgs, invocation.getInputEvent().getComponent()
                    ),
                )
            )
        return menuItems

    def genAddToES(self, msgs, component):
        def menuAddToES(e):
            progress = ProgressMonitor(
                component, "Feeding ElasticSearch", "", 0, len(msgs)
            )
            i = 0
            docs = list()
            for msg in msgs:
                if not Burp_onlyResponses or msg.getResponse():
                    docs.append(
                        self.genESDoc(msg, timeStampFromResponse=True).to_dict(True)
                    )
                i += 1
                progress.setProgress(i)
            success, failed = bulk(self.es, docs, True, raise_on_error=False)
            progress.close()
            JOptionPane.showMessageDialog(
                self.panel,
                "<html><p style='width: 300px'>Successful imported %d messages, %d messages failed.</p></html>"
                % (success, failed),
                "Finished",
                JOptionPane.INFORMATION_MESSAGE,
            )

        return menuAddToES

    ### Interface to ElasticSearch ###
    def genESDoc(self, msg, timeStampFromResponse=False):
        httpService = msg.getHttpService()
        doc = DocHTTPRequestResponse(
            protocol=httpService.getProtocol(),
            host=httpService.getHost(),
            port=httpService.getPort(),
        )
        doc.meta.index = self.confESIndex

        request = msg.getRequest()
        response = msg.getResponse()

        if request:
            doc.request.full = request.tostring().decode("utf-8", "replace")
            iRequest = self.helpers.analyzeRequest(msg)
            doc.request.method = iRequest.getMethod()
            doc.request.url = iRequest.getUrl().toString()

            headers = iRequest.getHeaders()
            for header in headers:
                try:
                    doc.add_request_header(header)
                except:
                    doc.request.requestline = header

            parameters = iRequest.getParameters()
            for parameter in parameters:
                ptype = parameter.getType()
                if ptype == IParameter.PARAM_URL:
                    typename = "url"
                elif ptype == IParameter.PARAM_BODY:
                    typename = "body"
                elif ptype == IParameter.PARAM_COOKIE:
                    typename = "cookie"
                elif ptype == IParameter.PARAM_XML:
                    typename = "xml"
                elif ptype == IParameter.PARAM_XML_ATTR:
                    typename = "xmlattr"
                elif ptype == IParameter.PARAM_MULTIPART_ATTR:
                    typename = "multipartattr"
                elif ptype == IParameter.PARAM_JSON:
                    typename = "json"
                else:
                    typename = "unknown"

                name = parameter.getName()
                value = parameter.getValue()
                doc.add_request_parameter(typename, name, value)

            ctype = iRequest.getContentType()
            if ctype == IRequestInfo.CONTENT_TYPE_NONE:
                doc.request.content_type = "none"
            elif ctype == IRequestInfo.CONTENT_TYPE_URL_ENCODED:
                doc.request.content_type = "urlencoded"
            elif ctype == IRequestInfo.CONTENT_TYPE_MULTIPART:
                doc.request.content_type = "multipart"
            elif ctype == IRequestInfo.CONTENT_TYPE_XML:
                doc.request.content_type = "xml"
            elif ctype == IRequestInfo.CONTENT_TYPE_JSON:
                doc.request.content_type = "json"
            elif ctype == IRequestInfo.CONTENT_TYPE_AMF:
                doc.request.content_type = "amf"
            else:
                doc.request.content_type = "unknown"

            bodyOffset = iRequest.getBodyOffset()
            doc.request.body = (
                request[bodyOffset:].tostring().decode("utf-8", "replace")
            )

        if response:
            doc.response.full = response.tostring().decode("utf-8", "replace")
            iResponse = self.helpers.analyzeResponse(response)

            doc.response.status = iResponse.getStatusCode()
            doc.response.content_type = iResponse.getStatedMimeType()
            doc.response.inferred_content_type = iResponse.getInferredMimeType()

            headers = iResponse.getHeaders()
            dateHeader = None
            for header in headers:
                try:
                    doc.add_response_header(header)
                    match = reDateHeader.match(header)
                    if match:
                        dateHeader = match.group(1)
                except:
                    doc.response.responseline = header

            cookies = iResponse.getCookies()
            for cookie in cookies:
                expCookie = cookie.getExpiration()
                expiration = None
                if expCookie:
                    try:
                        expiration = str(datetime.fromtimestamp(expCookie.time / 1000))
                    except:
                        pass
                doc.add_response_cookie(
                    cookie.getName(),
                    cookie.getValue(),
                    cookie.getDomain(),
                    cookie.getPath(),
                    expiration,
                )

            bodyOffset = iResponse.getBodyOffset()
            doc.response.body = (
                response[bodyOffset:].tostring().decode("utf-8", "replace")
            )

            if timeStampFromResponse:
                if dateHeader:
                    try:
                        doc.timestamp = datetime.fromtimestamp(
                            mktime_tz(parsedate_tz(dateHeader)), tz
                        )  # try to use date from response header "Date"
                        self.lastTimestamp = doc.timestamp
                    except:
                        doc.timestamp = (
                            self.lastTimestamp
                        )  # fallback: last stored timestamp. Else: now

        return doc
