// Main canvas — Caliper only, tightened.

const { useState } = React;

function App() {
  const firstModel = MODELS.multiboard[0];
  const [screen, setScreen] = useState("library"); // library | detail | print | cmdk
  const [current, setCurrent] = useState(firstModel);

  const openCmd = () => setScreen("cmdk");
  const openLib = () => setScreen("library");
  const openDetail = (m) => { setCurrent(m); setScreen("detail"); };
  const openPrint = () => setScreen("print");

  return (
    <DesignCanvas title="stuff — Caliper (refined)">

      <DCSection id="flows" title="Primary flows — library → detail → print prep">
        <DCArtboard id="cal-home" label="Library (desktop)" width={1360} height={820}>
          <CaliperHome onOpen={openDetail} onOpenCmd={openCmd} />
        </DCArtboard>
        <DCArtboard id="cal-detail" label="Model detail (desktop)" width={1440} height={860}>
          <CaliperDetail m={current} onBack={openLib} onOpenCmd={openCmd} onOpenPrint={openPrint} />
        </DCArtboard>
        <DCArtboard id="cal-print" label="Print prep (desktop)" width={1440} height={860}>
          <CaliperPrintPrep m={current} onBack={() => setScreen("detail")} onOpenCmd={openCmd} />
        </DCArtboard>
      </DCSection>

      <DCSection id="states" title="States — loading, error, empty, command palette">
        <DCArtboard id="cal-cmdk" label="Command palette (⌘K)" width={1440} height={860}>
          <CaliperCmdK onBack={openLib} onOpenCmd={openCmd} />
        </DCArtboard>
        <DCArtboard id="cal-loading" label="Loading" width={1440} height={860}>
          <CaliperDetail m={firstModel} onBack={openLib} onOpenCmd={openCmd} onOpenPrint={openPrint} initialState="loading" />
        </DCArtboard>
        <DCArtboard id="cal-error" label="Error" width={1440} height={860}>
          <CaliperDetail m={firstModel} onBack={openLib} onOpenCmd={openCmd} onOpenPrint={openPrint} initialState="error" />
        </DCArtboard>
        <DCArtboard id="cal-empty" label="Empty / idle" width={1440} height={860}>
          <CaliperDetail m={firstModel} onBack={openLib} onOpenCmd={openCmd} onOpenPrint={openPrint} initialState="empty" />
        </DCArtboard>
      </DCSection>

      <DCSection id="mobile" title="Mobile — bottom-sheet over live preview">
        <DCArtboard id="cal-mobile" label="Mobile detail (collapsed)" width={390} height={844}>
          <CaliperMobile m={firstModel} />
        </DCArtboard>
      </DCSection>

      <DCSection id="spec" title="Spec — share flow + shortcut + behavior reference">
        <DCArtboard id="cal-share" label="Share dialog + toast" width={1440} height={860}>
          <CaliperShareToast m={firstModel} onBack={openLib} onOpenCmd={openCmd} />
        </DCArtboard>
        <DCArtboard id="cal-shortcuts" label="Shortcuts + behavior + breakpoints" width={1440} height={1080}>
          <ShortcutSheet onBack={openLib} onOpenCmd={openCmd} />
        </DCArtboard>
      </DCSection>

    </DesignCanvas>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
