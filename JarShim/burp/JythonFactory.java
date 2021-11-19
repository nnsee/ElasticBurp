package burp;

import org.python.util.PythonInterpreter;

public class JythonFactory
{
    private static JythonFactory instance = null;
    public PythonInterpreter interpreter = null;
    public Object jyObject = null;

    public synchronized JythonFactory getInstance()
    {
        if (instance == null)
            instance = new JythonFactory();

        return instance;
    }

    public Object getJythonObject(String interfaceName, String pathToJythonModule)
    {
        interpreter = new PythonInterpreter();
        interpreter.exec("from " + pathToJythonModule + " import BurpExtender as ExtenderClass");

        String instanceName = pathToJythonModule.toLowerCase();
        String objectDef = " = ExtenderClass()";

        interpreter.exec(instanceName + objectDef);

        try
        {
            Class JavaInterface = Class.forName(interfaceName);
            jyObject = interpreter.get(instanceName).__tojava__(JavaInterface);
        }
        catch (ClassNotFoundException ex)
        {
            ex.printStackTrace();
        }

        return jyObject;
    }

}
