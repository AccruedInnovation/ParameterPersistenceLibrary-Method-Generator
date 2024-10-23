from __future__ import print_function
import sys, io, os
from copy import deepcopy
from datetime import datetime

start = datetime.now()

##########################################
######################## Todo list
##########################################

# set up way to flag POUs for reset/creation
# set up way to flag POUs to skip processing

##########################################
######################## Setup variables
##########################################

PersistProg = "SENSOR_PRG"
PersistFB = "SensorPersist"

warn_enums = True
enum_warning = "{warning 'PPL Unrecognized DATA TYPE, possible enum?'}\n"

filter_pou_names = False
# only selects POUs with the following filter
pou_name_filter = "_TEST"
debug = True
extendedDebug = False

rootClass = "EquipmentBaseClass"
intfName = "PersistIntf"

##########################################

POUGuid = Guid("6f9dac99-8de1-4efc-8465-68ac443b7d08")
folderGUID = Guid("738bea1e-99bb-4f04-90bb-a7a567e74e3a")
methodwithoutGUID = Guid("f89f7675-27f1-46b3-8abb-b7da8e774ffd")
methodGUID = Guid("f8a58466-d7f6-439f-bbb8-d4600e41d099")
DUTGuid = Guid("2db5746d-d284-4425-9f7f-2663a34b0ebc")

base_methods = [
    "AcceptValues",
    "CallEveryScan",
    "ProvideValues",
    "ProvideVarNames",
    "RegisterMySelf",
]

extended_methods = [
    "AcceptValues",
    "ProvideValues",
    "ProvideVarNames",
]

# lists of nodes
extended_nodes = []
implements_nodes = []
PPL_nodes = []
root_nodes = []
leaf_nodes = []
dut_nodes = []

extends_set = set()
implements_set = set()
extends_dict = {}
root_names = set()
leaf_names = set()
dut_set = set()
dut_dict = {}

# List to keep track of created PPL folders
# created_ppl_folders = []
# existing_ppl_folders = []

valid_dtypes = [
    "BOOL",
    "BYTE",
    "WORD",
    "DWORD",
    "LWORD",
    "SINT",
    "USINT",
    "INT",
    "UINT",
    "DINT",
    "UDINT",
    "LINT",
    "ULINT",
    "REAL",
    "LREAL",
    "STRING",
    "TIME",
    "LTIME",
    "DATE",
    "DATE_AND_TIME",
    "DT",
    "TIME_OF_DAY",
    "TOD",
    "LDATE",
    "LDATE_AND_TIME",
    "LDT",
    "LTIME_OF_DAY",
    "LTOD",
    "WSTRING",
    "BIT",
    "__UXINT",
    "__XINT",
    "__XWORD",
]

############################################################################
################################# CONFIG AND CLASSES
############################################################################

old_print = print


def timestamped_print(*args, **kwargs):
    old_print(datetime.now(), *args, **kwargs)


def debug_timestamped_print(*args, **kwargs):
    if debug:
        old_print(datetime.now(), *args, **kwargs)


def extended_debug_timestamped_print(*args, **kwargs):
    if extendedDebug:
        old_print(datetime.now(), *args, **kwargs)
        
print = timestamped_print
debugPrint = debug_timestamped_print
eDebugPrint = extended_debug_timestamped_print


class CI_Variables:
    def __init__(self):
        self.variables = []

    def add_variable(self, variable_name, data_type, friendly_name, valid=True):
        self.variables.append([variable_name, data_type, friendly_name, valid])

    def variable_count(self):
        return len(self.variables)

    def next_variable(self):
        return self.variables.pop(0)
        
    def pop_friendly_name(self):
        return self.variables.pop(0)[2]
        
    def pop_ProvideValues(self):
        popped = self.variables.pop(0)
        return popped[0], popped[3]
    
    def pop_AcceptValues(self):
        popped = self.variables.pop(0)
        return popped[0], popped[1], popped[3]
        
    def pop_variables(self):
        popped = self.variables.pop(0)
        return popped[0], popped[1], popped[2], popped[3]

    def __str__(self):
        return "\n".join(
            [
                "variable_name: {} data_type: {} friendly_name: {}".format(
                    var[0], var[1], var[2]
                )
                for var in self.variables
            ]
        )


class DUT_Variables(CI_Variables):
    def contains_DUTs(self):
        for var in self.variables:
            if var[1] in dut_set:
                return True
        
        return False


############################################################################
################################# PARSING
############################################################################


def ParseNodes(node):
    skip = True
    name = None

    if node.type in [POUGuid, DUTGuid]:
        name = node.get_name()

        skip = False
        declaration = node.textual_declaration.text

        if filter_pou_names:
            if pou_name_filter in name:
                skip = False
            else:
                skip = True
                debugPrint("Skipping {}".format(name))

    if not skip:
        if node.type == POUGuid:
            if name not in [extends_set, implements_set]:
                if "EXTENDS" in declaration:
                    eDebugPrint("Found POU: {}".format(name))
                    extended_nodes.append(node)
                    extends_set.add(name)
                else: # captures nodes that implement without extending
                    if "IMPLEMENTS" in declaration:
                        if intfName in declaration:
                            eDebugPrint("Found POU: {}".format(name))
                            implements_nodes.append(node)
                            implements_set.add(name)

        if node.type == DUTGuid:
            if name not in dut_set:
                if "//PPL" in declaration:
                    eDebugPrint("Found DUT: {}".format(name))
                    dut_nodes.append(node)
                    dut_set.add(name)


def BuildExtendedDict():
    eDebugPrint("Extended node count at start: {}".format(len(extended_nodes)))
    eDebugPrint("PPL node count at start: {}".format(len(PPL_nodes)))
    eDebugPrint("Root node count at start: {}".format(len(root_nodes)))
    
    for POU in extended_nodes:
        declaration = POU.textual_declaration
        name = POU.get_name()

        text = declaration.text.replace("\n", " ")
        split = text.split("EXTENDS")
        extends = split[1].strip().split(" ")[0]
        extends_dict[name] = extends
        eDebugPrint("{} EXTENDS {}".format(name, extends))

        if extends == rootClass and name not in root_names:
            PPL_nodes.append(POU)
            root_nodes.append(POU)
            root_names.add(name)
    
    for POU in implements_nodes:
        declaration = POU.textual_declaration
        name = POU.get_name()

        text = declaration.text
        split = text.split("IMPLEMENTS")
        # get text after implements up to first line break
        implements = split[1].strip().split("\n")[0]
        if intfName in implements:
            eDebugPrint("{} IMPLEMENTS {}".format(name, intfName))

            if name not in root_names:
                PPL_nodes.append(POU)
                root_nodes.append(POU)
                root_names.add(name)
                
    for POU in root_nodes:
        if POU in extended_nodes:
            extended_nodes.remove(POU)
        if POU in implements_nodes:
            implements_nodes.remove(POU)

    eDebugPrint("Extended node count at end: {}".format(len(extended_nodes)))
    eDebugPrint("PPL node count at end: {}".format(len(PPL_nodes)))
    eDebugPrint("Root node count at end: {}".format(len(root_nodes)))

    if extendedDebug:
        eDebugPrint("Extended nodes:".format(len(extended_nodes)))
        for POU in extended_nodes:
            print(POU.get_name())
        eDebugPrint("PPL nodes:".format(len(root_nodes)))
        for POU in root_nodes:
            print(POU.get_name())

        eDebugPrint("{} elements in Extended dict:".format(len(extends_dict)))
        for key, val in extends_dict.items():
            eDebugPrint("-{}- extends -{}-".format(key, val))


def FindMoreLeafNodes(group_number):
    foundLeafNodes = 0
    new_leaf_nodes = []

    for node in extended_nodes:
        node_name = node.get_name().strip()

        if extends_dict[node_name] in leaf_names and node_name not in leaf_names:
            PPL_nodes.append(node)
            leaf_nodes.append(node)
            new_leaf_nodes.append(node)
            leaf_names.add(node_name)

            foundLeafNodes = foundLeafNodes + 1

    for POU in new_leaf_nodes:
        extended_nodes.remove(POU)

    if foundLeafNodes > 0:
        debugPrint("Group {}: found: {}".format(group_number, foundLeafNodes))
        # Print the POUs in the target group
        if extendedDebug:
            for POU in new_leaf_nodes:
                print(
                    "Group {}: found: {} {} {}".format(
                        group_number, POU.type, POU.guid, POU.get_name()
                    )
                )
    else:
        debugPrint("Group {}: no leaf nodes found".format(group_number))

    return foundLeafNodes


def FindAllLeafNodes():
    foundLeafNodes = 0

    for node in extended_nodes:
        node_name = node.get_name().strip()

        if extends_dict[node_name] in root_names and node not in leaf_nodes:
            PPL_nodes.append(node)
            leaf_nodes.append(node)
            leaf_names.add(node_name)

            foundLeafNodes = foundLeafNodes + 1

    for POU in leaf_nodes:
        extended_nodes.remove(POU)

    if foundLeafNodes > 0:
        debugPrint("Group 0: found: {}".format(foundLeafNodes))
        # Print the POUs in the target group
        if extendedDebug:
            for POU in leaf_nodes:
                print("Group 0: found: {}".format(POU.get_name()))

        foundLeafNodes = 0
        i = 0

        while True:
            i = i + 1
            foundLeafNodes = FindMoreLeafNodes(i)
            if foundLeafNodes == 0:
                break
    else:
        print("WARNING: no leaf nodes found")


def Extract_DUT_Variables(DUT):
    dut_variables = DUT_Variables()
    name = DUT.get_name()
    declaration = DUT.textual_declaration
    has_ci = False
    eDebugPrint(name)

    for i in range(0, declaration.linecount):
        valid = False
        line = declaration.get_line(i)

        # Extract variable name and data type
        parts = line.split(":")

        if len(parts) >= 2:
            variable_name = parts[0].strip()

            # stop if it's been commented out
            if variable_name[0:2] == "//":
                continue

            has_ci = "_CI" in line

            if has_ci:
                # remove last 3 characters _CI from variable name
                friendly_name = variable_name[:-3]
                eDebugPrint("{} has _CI".format(variable_name))
            else:
                friendly_name = variable_name

            data_type = parts[1].strip()

            # converts STRING(###) to STRING
            data_type = data_type.split("(")[0]

            # removes trailing semicolon
            data_type = data_type.split(";")[0]

            valid = (has_ci and (data_type in valid_dtypes)) or (data_type in dut_set)

            if valid:
                dut_variables.add_variable(
                    variable_name, data_type, friendly_name, valid
                )

    if dut_variables.variable_count() > 0:
        return dut_variables
    else:
        return False


def BuildDUTDict():
    # first pass to collect all CI and DUT variables
    for DUT in dut_nodes:
        name = DUT.get_name()
        DUT_vars = Extract_DUT_Variables(DUT)
        dut_dict[name] = DUT_vars

    changed = False
    # recursively expand all DUT variables
    while not changed:
        changed = DUTTreeCheck()


def Expand_DUT_Variables(DUT_vars):
    New_vars = DUT_Variables()

    for _ in range(0, DUT_vars.variable_count()):
        variable_name, data_type, friendly_name, valid = DUT_vars.pop_variables()

        if data_type in dut_set:
            # make a deep copy of the vars so we don't affect the original
            Embedded_vars = deepcopy(dut_dict[data_type])
            for _ in range(0, Embedded_vars.variable_count()):
                ev_name, ed_type, ef_name, evalid = Embedded_vars.pop_variables()
                nv_name = variable_name + "." + ev_name

                if variable_name[-3] == "_CI":
                    nf_name = variable_name[:-3] + "." + ef_name
                else:
                    nf_name = variable_name + "." + ef_name

                New_vars.add_variable(nv_name, ed_type, nf_name, evalid)
        else:
            New_vars.add_variable(variable_name, data_type, friendly_name, valid)

    return New_vars


def DUTTreeCheck():
    changed = False
    for DUT in dut_nodes:
        name = DUT.get_name()
        if dut_dict[name].contains_DUTs():
            DUT_vars = dut_dict.pop(name)
            New_vars = Expand_DUT_Variables(DUT_vars)
            dut_dict[name] = New_vars
            changed = True

    return changed


def Parse_CI_Variables(POU):
    pou_variables = CI_Variables()
    declaration = POU.textual_declaration

    for i in range(0, declaration.linecount):
        line = declaration.get_line(i)
        if "_CI" in line:
            # Extract variable name and data type

            parts = line.split(":")

            if len(parts) >= 2:
                variable_name = parts[0].strip()

                # stop if it's been commented out
                if variable_name[0:2] == "//":
                    continue

                # stop if the first group is not the config variable
                if "_CI" not in variable_name:
                    continue

                # remove last 3 characters _CI from variable name for friendly name
                friendly_name = variable_name[:-3]

                data_type = parts[1].strip()

                # converts STRING(###) to STRING
                data_type = data_type.split("(")[0]

                # removes trailing semicolon
                data_type = data_type.split(";")[0]

                valid = data_type in valid_dtypes

                if not valid and data_type in dut_set:
                    Embedded_vars = deepcopy(dut_dict[data_type])
                    for i in range(0, Embedded_vars.variable_count()):
                        ev_name, ed_type, ef_name, evalid = (
                            Embedded_vars.pop_variables()
                        )
                        nv_name = variable_name + "." + ev_name
                        nf_name = (
                            variable_name[:-3] + "." + ef_name
                        )  # drop _CI for friendly
                        pou_variables.add_variable(nv_name, ed_type, nf_name, evalid)
                else:
                    pou_variables.add_variable(
                        variable_name, data_type, friendly_name, valid
                    )

    if pou_variables.variable_count() > 0:
        return pou_variables
    else:
        return False


############################################################################
################################# FOLDER STUFF
############################################################################


def Return_PPL_Folder(POU):
    for child in POU.get_children():
        if child.type == folderGUID and child.get_name() == "PPL":
            return child
    return False


def Remove_PPL_Folder(POU):
    folder = Return_PPL_Folder(POU)
    if folder:
        folder.remove()


def Check_For_PPL_Folder(POU):
    if Return_PPL_Folder(POU):
        return True
    return False


def Ensure_PPL_Folder(POU):
    pou_name = POU.get_name()

    # returns folder if found, else False
    folder = Return_PPL_Folder(POU)

    if folder:
        eDebugPrint("PPL folder already exists in {}".format(pou_name))
        # existing_ppl_folders.append([POU, folder])
        return folder
    else:  # Create 'PPL' folder
        POU.create_folder("PPL")
        folder = Return_PPL_Folder(POU)
        # created_ppl_folders.append([POU, folder])
        debugPrint("Created PPL folder in {}".format(pou_name))

    return folder


############################################################################
################################# METHOD CONSTRUCTION
############################################################################

def AddRootPOUDeclaration(POU):
    # Check if 'StoreConfig_VI' is in the POU's declaration
    declaration = POU.textual_declaration

    # Add PersistIntf variables
    if "StoreConfig_VI" not in declaration.text:
        # Define the code block to be added

        code_block = """
VAR //required for "IMPLEMENTS PersistIntf"
    {attribute 'symbol' := 'readwrite'}
    StoreConfig_VI : BOOL; //commands the global configurator to store the current configuration for this instance
    MyConfigRegistrationNumber : INT;
    MyType : String := __POUNAME();
END_VAR
"""
        # Insert the code block at the end of the declaration
        declaration.append(code_block)
        debugPrint("Added code block to {0}".format(POU.get_name()))


def FindCommentedIntf(POU, replace=False):
    declaration = POU.textual_declaration

    foundComment = False
    foundCommentIntf = False
    foundIntf = False

    for i in range(0, declaration.linecount):
        line = declaration.get_line(i)
        if intfName in line:
            foundIntf = True
            parts = line.split("//")
            if len(parts) >= 2:
                foundComment = True

            eDebugPrint(line)

    if foundComment:
        for j in range(0, len(parts)):
            if intfName in parts[j]:
                newLine = line.replace("//", "")
                eDebugPrint("Found Commented Interface in {0}".format(POU.get_name()))
                foundCommentIntf = True

    if foundCommentIntf and replace:
        declaration.replace_line(i, newLine)
        eDebugPrint("Replaced Commented Interface in {0}".format(POU.get_name()))
        
    return foundIntf, foundCommentIntf


def UncommentIntf(POU):
    FindCommentedIntf(POU, replace=True)


def RootPOUUpdates(group):
    for POU in group:
        AddRootPOUDeclaration(POU)


def Is_Method_Guid(POU):
    if POU.type == methodwithoutGUID or POU.type == methodGUID:
        return True
    return False


def Clear_Text_Object(ScriptTextDocument):
    ScriptTextDocument.remove(length=ScriptTextDocument.length, offset=0)
    return


def Clear_All_Method_Texts(method):
    Clear_Text_Object(method.textual_implementation)
    Clear_Text_Object(method.textual_declaration)
    return


def Get_or_Make_Method(folder, methodName):
    # Find the method
    method = None

    for child in folder.get_children():
        if child.get_name() == methodName:
            method = child
            break

    if not method:
        eDebugPrint("{} not found, creating".format(methodName))
        folder.create_method(methodName)
        method = Get_or_Make_Method(folder, methodName)

    return method


def Remove_Unfoldered_Methods(POU):
    for child in POU.get_children():
        if not Is_Method_Guid(child):
            continue
        if child.get_name() in base_methods:
            debugPrint(
                "Unfoldered {} removed from {}".format(child.get_name(), POU.get_name())
            )
            child.remove()

    return


############################################################################
################################# DECLARATIONS
############################################################################


def Create_PPL_Declaration_Text(name, extended=False):
    # Create the method declaration
    code_block = (
        "METHOD "
        + name
        + """ : INT
VAR_INPUT
	PersistGroupNum : INT; //Persistence Group Number
END_VAR
VAR_IN_OUT
	ValueArray	: ARRAY [*] OF STRING(PPL_GlobalConstants.gc_MaxParameterSize);
END_VAR
"""
    )
    if extended:
        code_block = (
            code_block
            + """VAR
	LastValue : INT;
END_VAR"""
        )

    return code_block


def Create_PPL_Declaration(method, extended=False):
    # Create the method declaration
    code_block = Create_PPL_Declaration_Text(method.get_name(), extended=extended)
    declaration = method.textual_declaration
    declaration.append(code_block)
    if extended:
        eDebugPrint("Created extended declaration")
    else:
        eDebugPrint("Created standard declaration")
    return


def Create_Extended_PPL_Declaration(method):
    Create_PPL_Declaration(method, extended=True)
    return


############################################################################
################################# IMPLEMENTATIONS
############################################################################


def Create_Standard_AcceptValues_Implementation(method, POU_Variables):
    # Create the method implementation
    code_block = "ISA_Name_CI := ValueArray[0];\n"

    var_count = POU_Variables.variable_count()

    arrayNum = 0

    for i in range(0, var_count):
        variable_name, data_type, valid = POU_Variables.pop_AcceptValues()

        if warn_enums and not valid:
            code_block += enum_warning

        arrayNum = i + 1
        code_block += (
            variable_name
            + " := TO_"
            + data_type
            + "(ValueArray["
            + str(arrayNum)
            + "]);\n"
        )

    arrayNum = arrayNum + 1

    code_block += "AcceptValues := " + str(arrayNum) + ";\n\n"

    code_block += "IF AcceptValues-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created AcceptValues implementation")
    return


def Create_Extended_AcceptValues_Implementation(method, POU_Variables):
    # Create the method implementation
    code_block = """LastValue := SUPER^.AcceptValues(
	PersistGroupNum := PersistGroupNum,
	ValueArray := ValueArray
);

"""
    lastValue_increment_block = """LastValue := LastValue + 1;\n"""

    last_code_block = """
AcceptValues := LastValue;

IF AcceptValues-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"""

    var_count = POU_Variables.variable_count()

    for _ in range(0, var_count):
        variable_name, data_type, valid = POU_Variables.pop_AcceptValues()

        if warn_enums and not valid:
            code_block += enum_warning

        code_block += (
            variable_name
            + " := TO_"
            + data_type
            + "(ValueArray[LastValue]);\n"
            + lastValue_increment_block
        )

    code_block += last_code_block

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created extended AcceptValues implementation")
    return


def Create_Standard_ProvideValues_Implementation(method, POU_Variables):
    # Create the method implementation
    code_block = "ValueArray[0] := MyName;\n"

    var_count = POU_Variables.variable_count()

    arrayNum = 0

    for i in range(0, var_count):
        variable_name, valid = POU_Variables.pop_ProvideValues()

        if warn_enums and not valid:
            code_block += enum_warning

        arrayNum = i + 1
        code_block += (
            "ValueArray[" + str(arrayNum) + "] := TO_STRING(" + variable_name + ");\n"
        )

    arrayNum = arrayNum + 1

    code_block += "ProvideValues := " + str(arrayNum) + ";\n\n"

    code_block += "IF ProvideValues-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created ProvideValues implementation")
    return


def Create_Extended_ProvideValues_Implementation(method, POU_Variables):
    # Create the method implementation
    implementation = method.textual_implementation

    code_block = """LastValue := SUPER^.ProvideValues(
	PersistGroupNum := PersistGroupNum,
	ValueArray := ValueArray
);

"""
    lastValue_increment_block = """LastValue := LastValue + 1;\n"""

    last_code_block = """
ProvideValues := LastValue;

IF ProvideValues-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"""

    var_count = POU_Variables.variable_count()

    for _ in range(0, var_count):
        variable_name, valid = POU_Variables.pop_ProvideValues()

        if warn_enums and not valid:
            code_block += enum_warning

        code_block += (
            "ValueArray[LastValue] := TO_STRING("
            + variable_name
            + ");\n"
            + lastValue_increment_block
        )

    code_block += last_code_block

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created extended ProvideValues implementation")
    return


def Create_Standard_ProvideVarNames_Implementation(method, POU_Variables):
    # Create the method implementation
    code_block = "ValueArray[0] := 'ISA_Name';\n"

    var_count = POU_Variables.variable_count()
    arrayNum = 0

    for i in range(0, var_count):
        friendly_name = POU_Variables.pop_friendly_name()

        arrayNum = i + 1
        code_block += "ValueArray[" + str(arrayNum) + "] := '" + friendly_name + "';\n"

    arrayNum = arrayNum + 1

    code_block += "ProvideVarNames := " + str(arrayNum) + ";\n\n"

    code_block += "IF ProvideVarNames-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created ProvideVarNames implementation")
    return


def Create_Extended_ProvideVarNames_Implementation(method, POU_Variables):
    # Create the method implementation
    code_block = """LastValue := SUPER^.ProvideVarNames(
	PersistGroupNum := PersistGroupNum,
	ValueArray := ValueArray
);

"""
    lastValue_increment_block = """LastValue := LastValue + 1;\n"""

    last_code_block = """
ProvideVarNames := LastValue;

IF ProvideVarNames-1 > UPPER_BOUND(ValueArray,1) THEN LogMsgAndPopup('gc_MaxConfigParameters too small'); END_IF"""

    var_count = POU_Variables.variable_count()

    for _ in range(0, var_count):
        friendly_name = POU_Variables.pop_friendly_name()

        code_block += (
            "ValueArray[LastValue] := '"
            + friendly_name
            + "';\n"
            + lastValue_increment_block
        )

    code_block += last_code_block

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created extended ProvideVarNames implementation")
    return


############################################################################
################################# METHOD ASSEMBLIES
############################################################################


def Create_Standard_AcceptValues(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "AcceptValues")

    Clear_All_Method_Texts(method)

    Create_PPL_Declaration(method)
    Create_Standard_AcceptValues_Implementation(method, POU_Variables)

    eDebugPrint("Created AcceptValues")
    return


def Create_Extended_AcceptValues(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "AcceptValues")

    Clear_All_Method_Texts(method)
    Create_Extended_PPL_Declaration(method)

    Create_Extended_AcceptValues_Implementation(method, POU_Variables)
    eDebugPrint("Created extended AcceptValues")
    return


def Create_Standard_ProvideValues(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "ProvideValues")

    Clear_All_Method_Texts(method)

    Create_PPL_Declaration(method)
    Create_Standard_ProvideValues_Implementation(method, POU_Variables)

    eDebugPrint("Created ProvideValues")
    return


def Create_Extended_ProvideValues(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "ProvideValues")

    Clear_All_Method_Texts(method)
    Create_Extended_PPL_Declaration(method)

    Create_Extended_ProvideValues_Implementation(method, POU_Variables)
    eDebugPrint("Created extended ProvideValues")
    return


def Create_Standard_ProvideVarNames(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "ProvideVarNames")

    Clear_All_Method_Texts(method)

    Create_PPL_Declaration(method)
    Create_Standard_ProvideVarNames_Implementation(method, POU_Variables)

    eDebugPrint("Created ProvideVarNames")
    return


def Create_Extended_ProvideVarNames(folder, POU_Variables):
    method = Get_or_Make_Method(folder, "ProvideVarNames")

    Clear_All_Method_Texts(method)

    Create_Extended_PPL_Declaration(method)
    Create_Extended_ProvideVarNames_Implementation(method, POU_Variables)
    eDebugPrint("Created extended ProvideVarNames")
    return


def Create_CallEveryScan(folder, Program="PersistProg", FB="Persist"):
    method = Get_or_Make_Method(folder, "CallEveryScan")

    Clear_All_Method_Texts(method)

    # Declaration
    declaration = method.textual_declaration
    declaration.append("METHOD CallEveryScan\n")

    # Implementation
    locString = Program + "." + FB + "."

    code_block = """IF StoreConfig_VI THEN 
	StoreConfig_VI := FALSE;
    """

    code_block += (
        locString
        + """WriteChangeFileSync(THIS^, 0,"""
        + locString
        + """ChangeFileName_VI, MyPath);
END_IF"""
    )

    implementation = method.textual_implementation
    implementation.append(code_block)

    eDebugPrint("Created CallEveryScan")
    return


def Create_RegisterMySelf(folder, Program="PersistProg", FB="Persist"):
    method = Get_or_Make_Method(folder, "RegisterMySelf")

    Clear_All_Method_Texts(method)

    # Declaration
    declaration = method.textual_declaration
    dec_block = """{attribute 'call_after_global_init_slot' := '10001'}
{attribute 'call_after_online_change_slot' := '10001'}
METHOD RegisterMySelf"""
    declaration.append(dec_block)

    # Implementation
    implementation = method.textual_implementation
    locString = Program + "." + FB + "."

    code_block = """MyConfigRegistrationNumber := 
    """

    code_block += (
        locString
        + """RecieveObjectRegistration
		(THIS^, MyType, MyPath);"""
    )

    implementation.append(code_block)

    eDebugPrint("Created RegisterMySelf")
    return


def Create_Standard_Methods(POU, Program="PersistProg", FB="Persist"):
    name = POU.get_name()
    eDebugPrint("Creating standard methods for {}".format(name))

    Remove_Unfoldered_Methods(POU)
    POU_Variables = Parse_CI_Variables(POU)
    
    foundIntf, foundCommentIntf = FindCommentedIntf(POU)

    if not POU_Variables:
        if foundIntf:
            print("ERROR NO _CI variables found in POU {}".format(name))
            
        Remove_PPL_Folder(POU)
        return

    folder = Ensure_PPL_Folder(POU)
    
    AddRootPOUDeclaration(POU)
    
    if foundCommentIntf:
        UncommentIntf(POU)

    Create_Standard_AcceptValues(folder, deepcopy(POU_Variables))
    Create_Standard_ProvideVarNames(folder, deepcopy(POU_Variables))
    Create_Standard_ProvideValues(folder, POU_Variables)
    Create_CallEveryScan(folder, Program=Program, FB=FB)
    Create_RegisterMySelf(folder, Program=Program, FB=FB)

    eDebugPrint("DONE creating standard methods for {}".format(name))
    return


def Create_Extended_Methods(POU):
    name = POU.get_name()
    eDebugPrint("Creating extended methods for {}".format(name))

    Remove_Unfoldered_Methods(POU)
    POU_Variables = Parse_CI_Variables(POU)

    if not POU_Variables:
        debugPrint("WARNING NO Additional _CI variables found in extended POU {}".format(name))
        Remove_PPL_Folder(POU)
        return

    folder = Ensure_PPL_Folder(POU)
    UncommentIntf(POU)

    Create_Extended_AcceptValues(folder, deepcopy(POU_Variables))
    Create_Extended_ProvideVarNames(folder, deepcopy(POU_Variables))
    Create_Extended_ProvideValues(folder, POU_Variables)

    eDebugPrint("DONE creating extended methods for {}".format(name))
    return


############################################################################
################################# RUN SCRIPT
############################################################################

print("START")

# Set target Project to primary
proj = projects.primary

# get script's current directory
ScriptPath = os.path.dirname(os.path.realpath(__file__))

# get all nodes
all_nodes = proj.get_children(True)


##########################################
######################## Collect all PPL POUs
##########################################

debugPrint("Collect all EXTENDed")
for node in all_nodes:
    ParseNodes(node)

if extendedDebug:
    for name in dut_set:
        print(name)

BuildExtendedDict()

BuildDUTDict()

# extendedDebug = True

if extendedDebug:
    for key, val in dut_dict.items():
        debugPrint(key)
        debugPrint(val)

extendedDebug = False

FindAllLeafNodes()

# extendedDebug = True

for POU in root_nodes:
    Create_Standard_Methods(POU, Program=PersistProg, FB=PersistFB)

for POU in leaf_nodes:
    Create_Extended_Methods(POU)

print("DONE! Script runtime: {}".format(datetime.now()-start))