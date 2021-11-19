package burp;

import burp.JythonFactory;
import java.io.ByteArrayOutputStream;

public class BurpExtender
{

    private static IBurpExtender handler;
    private JythonFactory jf = null;

    public BurpExtender()
    {
        if (handler == null)
        {
            jf = new JythonFactory();
            BurpExtender.handler = (IBurpExtender) jf
                    .getJythonObject(IBurpExtender.class.getName(),
                            "ElasticBurp");

        }
    }

    public static IBurpExtender getHandler()
    {
        return handler;
    }

    public static void setHandler(IBurpExtender handle)
    {
        handler = handle;
    }

    public void registerExtenderCallbacks(IBurpExtenderCallbacks callbacks)
    {
        handler.registerExtenderCallbacks(callbacks);
        jf.interpreter.setOut(callbacks.getStdout());
        jf.interpreter.setErr(callbacks.getStderr());
    }

}
