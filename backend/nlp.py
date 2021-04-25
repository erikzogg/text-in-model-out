import spacy
import lemminflect
from spacy import displacy
from spacy.lang.en.stop_words import STOP_WORDS
from pathlib import Path


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    elements = []

    for sent in doc.sents:
        verbs = [token for token in sent if token.pos_ == "VERB"]

        for verb in verbs:
            condition = detect_condition(verb)

            if condition:
                if condition != "semimodal":
                    elements.append({"type": "condition", "condition": condition})

                continue

            if detect_parallel(verb):
                elements.insert(len(elements) - 1, {"type": "parallel"})
                elements.append({"type": "change_flow"})

            if detect_flowchange(verb):
                elements.append({"type": "change_flow"})

            if detect_join(verb):
                elements.append({"type": "join_flow"})
                continue

            if is_semimodal(verb):
                continue

            the_object = get_the_object(verb)

            if not the_object:
                continue

            advmod = next((child for child in verb.children if (child.dep_ == "advmod" and child.text.lower() in ["once", "after"])), None)

            if advmod:
                elements.append({"type": "verb", "object": the_object, "verb": verb, "event": True})
            else:
                elements.append({"type": "verb", "object": the_object, "verb": verb, "event": False})

    return parse_elements(elements)


def detect_join(verb):
    nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass" and child.text.lower() in ["the sequence flow", "the flow"])), None)

    if verb.lemma_ == "merge" and nsubjpass:
        return True

    return False


def detect_condition(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)  # ToDo

    if parent_verb:
        mark = next((child for child in parent_verb.children if (child.dep_ == "mark" and child.text.lower() in ["if"])), None)

        if mark:
            return "semimodal"
    else:
        mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in ["if"])), None)

    if mark:
        if passive:
            nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

            return nsubjpass.text + " " + verb.text + "?"
        else:
            nsubj = next((child for child in verb.children if (child.dep_ == "nsubj")), None)
            aux = next((child for child in verb.children if (child.dep_ == "aux")), None)
            negative = next((child for child in verb.children if (child.dep_ == "neg" and child in verb.lefts)), None)
            dobj = next((child for child in verb.children if (child.dep_ == "dobj")), None)

            if not dobj:
                neighbor_children = list(verb.rights)
                condition_text = []

                while neighbor_children:
                    for child in neighbor_children:
                        condition_text.append(child.text)
                        neighbor_children.remove(child)
                        if child.rights:
                            for subchild in child.rights:
                                neighbor_children.append(subchild)

                dobj = " ".join(condition_text)
            else:
                dobj = dobj.text

            conditional_label = nsubj.text

            if aux:
                conditional_label += " " + aux.text

            if negative:
                conditional_label += " " + negative.text

            conditional_label += " " + verb.text + " " + dobj + "?"

            return conditional_label

    prep = next((child for child in verb.children if (child.dep_ == "prep")), None)

    if prep:
        pobj = next((child for child in prep.children if (child.dep_ == "pobj")), None)

        if pobj:
            conditional_conj = prep.lemma_ + " " + pobj.lemma_

            if conditional_conj.lower() in ["for the case", "in case", "in the case"]:
                neighbor = pobj.nbor()
                condition_text = [neighbor.text]

                while neighbor.text:
                    neighbor = neighbor.nbor()

                    if neighbor.text == ",":
                        break

                    condition_text.append(neighbor.text)

                condition_text = " ".join([word for word in condition_text if word.lower() not in ["a", "an", "of", "that", "the"]]).title() + "?"

                return condition_text

    return False


def detect_parallel(verb):
    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in ["while"])), None)

    if mark:
        return True

    return False


def detect_flowchange(verb):
    advmod = next((child for child in verb.children if (child.dep_ == "advmod" and child.text.lower() in ["alternatively", "else", "otherwise"])), None)

    if advmod:
        return True

    return False


def is_semimodal(verb):
    has_xcomp = next((child for child in verb.children if (child.dep_ == "xcomp")), None)

    if has_xcomp:
        return True
    else:
        return False


def get_parent_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "xcomp")), None)


def is_passive(verb):
    has_auxpass = next((child for child in verb.children if (child.dep_ == "auxpass")), None)
    has_nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

    if has_auxpass and has_nsubjpass:
        return True
    else:
        return False


def get_the_object(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)

    if parent_verb:
        passive = is_passive(parent_verb)

        if passive:
            the_object = next((child for child in parent_verb.children if (child.dep_ == "nsubjpass")), None)
        else:
            the_object = next((child for child in verb.children if (child.dep_ == "dobj")), None)

            if not the_object:
                has_auxpass = next((child for child in verb.children if (child.dep_ == "auxpass")), None)

                if has_auxpass:
                    the_object = next((child for child in parent_verb.children if (child.dep_ == "nsubj")), None)
    elif not passive:
        the_object = next((child for child in verb.children if (child.dep_ == "dobj")), None)

        if not the_object:
            prep = next((child for child in verb.rights if (child.dep_ == "prep")), None)

            if prep:
                neighbor_children = list(prep.rights)
                condition_text = [prep.text]

                while neighbor_children:
                    for child in neighbor_children:
                        if child.is_punct is False:
                            condition_text.append(child.text)
                        neighbor_children.remove(child)
                        if child.rights:
                            for subchild in child.rights:
                                neighbor_children.append(subchild)

                the_object = " ".join(condition_text)

                return the_object

            conj = next((child for child in verb.children if (child.dep_ == "conj")), None)

            if conj:
                return get_the_object(conj)
        else:
            prep = next((child for child in verb.rights if (child.dep_ == "prep")), None)

            if prep:
                neighbor_children = list(prep.rights)
                condition_text = [prep.text]

                while neighbor_children:
                    for child in neighbor_children:
                        if child.is_punct is False:
                            condition_text.append(child.text)
                        neighbor_children.remove(child)
                        if child.rights:
                            for subchild in child.rights:
                                neighbor_children.append(subchild)

                return the_object.lemma_ + " " + " ".join(condition_text)
    else:
        the_object = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

        prep = next((child for child in verb.rights if (child.dep_ == "prep")), None)

        if prep and the_object:
            neighbor_children = list(prep.rights)
            condition_text = [prep.text]

            while neighbor_children:
                for child in neighbor_children:
                    if child.is_punct is False:
                        condition_text.append(child.text)
                    neighbor_children.remove(child)
                    if child.rights:
                        for subchild in child.rights:
                            neighbor_children.append(subchild)

            the_object = the_object.lemma_ + " " + " ".join(condition_text)

            return the_object
    if the_object:
        return the_object.lemma_
    else:
        return None


def get_phrasal_verb(verb):
    phrasal_verb = next((child for child in verb.children if (child.dep_ == "prt")), None)

    return phrasal_verb


def get_actor(verb):
    passive = is_passive(verb)
    parent_verb = get_parent_verb(verb)

    if parent_verb:
        agent = next((child for child in verb.children if (child.dep_ == "agent")), None)
        has_auxpass = next((child for child in verb.children if (child.dep_ == "auxpass")), None)

        if agent:
            actor = next((child for child in agent.children if (child.dep_ == "pobj")), None)
        elif not has_auxpass:
            actor = next((child for child in parent_verb.children if (child.dep_ == "nsubj")), None)
        else:
            actor = None
    elif not passive:
        actor = next((child for child in verb.children if (child.dep_ == "nsubj")), None)
    else:
        agent = next((child for child in verb.children if (child.dep_ == "agent")), None)

        if agent:
            actor = next((child for child in agent.children if (child.dep_ == "pobj")), None)
        else:
            actor = None

    return actor


def parse_elements(elements):
    result = []

    current_actor = "Default"
    predecessor = None
    last_gateway = None
    last_element = None
    predecessors = []
    split_gateways = {}

    for element in elements:
        if element["type"] == "verb":
            the_object = element['object']
            verb = element['verb']
            phrasal_verb = get_phrasal_verb(verb)  # hand in, set up, ...

            the_object = " ".join([word for word in the_object.split() if word.lower() not in ["a", "an", "the"]])

            actor = get_actor(verb)

            if actor:
                actor = " ".join([word for word in actor.lemma_.split() if word.lower() not in STOP_WORDS]).title()

                if actor != "":
                    current_actor = actor

            if element == elements[0] or element["event"] is True:
                if element == elements[0]:
                    type = "bpmn:StartEvent"
                else:
                    type = "bpmn:IntermediateThrowEvent"

                if not phrasal_verb:
                    value = (the_object + " " + verb._.inflect("VBN")).title()
                    element_id = "".join(value.split())
                    result.append({"type": type, "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})
                    predecessor = element_id
                else:
                    value = (the_object + " " + verb._.inflect("VBN") + " " + phrasal_verb.lemma_).title()
                    element_id = "".join(value.split())
                    result.append({"type": type, "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})
                    predecessor = element_id
            else:
                if not phrasal_verb:
                    value = (verb.lemma_ + " " + the_object).title()
                    element_id = "".join(value.split())
                    result.append({"type": "bpmn:Task", "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})
                    predecessor = element_id
                else:
                    value = (verb.lemma_ + " " + phrasal_verb.lemma_ + " " + the_object).title()
                    element_id = "".join(value.split())
                    result.append({"type": "bpmn:Task", "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})
                    predecessor = element_id

            last_element = element_id
        elif element["type"] == "condition":
            value = " ".join([word for word in element["condition"].split() if word.lower() not in ["a", "an", "the"]]).title()
            element_id = "".join(value.split())
            result.append({"type": "bpmn:ExclusiveGateway", "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})
            predecessor = last_gateway = element_id
            predecessors = []
            split_gateways[element_id] = []
        elif element["type"] == "change_flow":
            predecessor = last_gateway
            predecessors.append(last_element)
            split_gateways[last_gateway].append(last_element)
        elif element["type"] == "join_flow":
            element_id = last_gateway + "_join"
            split_gateways[last_gateway].append(predecessor)
            predecessors.append(predecessor)
            if "ParallelGateway" in last_gateway:
                result.append({"type": "bpmn:ParallelGateway", "value": "", "id": element_id, "actor": current_actor, "predecessors": split_gateways[last_gateway]})
            else:
                result.append({"type": "bpmn:ExclusiveGateway", "value": "", "id": element_id, "actor": current_actor, "predecessors": split_gateways[last_gateway]})
            predecessor = element_id
            predecessors = []

            split_gateways.pop(last_gateway, None)
            if len(split_gateways) > 0:
                last_gateway = list(split_gateways)[-1]
            else:
                last_gateway = None
        elif element["type"] == "parallel":
            element_id = predecessor + "_ParallelGateway"
            result.append({"type": "bpmn:ParallelGateway", "value": "", "id": element_id, "actor": current_actor, "predecessor": predecessor})
            predecessor = last_gateway = element_id
            predecessors = []
            split_gateways[element_id] = []

    for key, value in split_gateways.items():
        result.append({"type": "bpmn:EndEvent", "value": "", "id": value[-1] + "_end", "actor": current_actor, "predecessor": value[-1]})

    tasks = list(element for element in elements if element["type"] == "verb")

    if tasks:
        last_task = tasks[-1]

        the_object = last_task["object"]
        verb = last_task["verb"]
        phrasal_verb = get_phrasal_verb(verb)
        the_object = " ".join([word for word in the_object.split() if word.lower() not in ["a", "an", "the"]])

        actor = get_actor(verb)

        if actor:
            actor = " ".join([word for word in actor.lemma_.split() if word.lower() not in STOP_WORDS]).title()

            if actor != "":
                current_actor = actor

        if not phrasal_verb:
            value = (the_object + " " + verb._.inflect("VBN")).title()
            element_id = "".join(value.split())
        else:
            value = (the_object + " " + verb._.inflect("VBN") + " " + phrasal_verb.lemma_).title()
            element_id = "".join(value.split())

        result.append({"type": "bpmn:EndEvent", "value": value, "id": element_id, "actor": current_actor, "predecessor": predecessor})

    return result
