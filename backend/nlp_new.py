import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

exclusive_markers = ["if", "in case", "in the case", "for the case"]
parallel_markers = ["while", "at the same time"]
sequence_flow_change_markers = ["otherwise", "in the other case"]
sequence_flow_join_markers = ["the sequence flow", "the flow", "once one of these activities", "once these activities", "after each of these activities", "after these activities"]
sequence_flow_join_verbs = ["merge", "perform", "complete", "execute"]
process_termination_markers = ["the business process", "this business process", "the process", "this process"]
process_termination_verbs = ["end", "finish", "stop", "terminate"]


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    triggers = parse_verbs(doc)
    elements = parse_triggers(triggers)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return elements


def parse_verbs(doc):
    triggers = []

    for sent in doc.sents:
        verbs = [token for token in sent if token.pos_ == "VERB"]

        for verb in verbs:
            exclusive_gateway = detect_exclusive_gateway(verb)

            if exclusive_gateway:
                if exclusive_gateway == verb:
                    triggers.append({"category": "exclusive_gateway", "verb": verb})

                continue

            parallel_gateway = detect_parallel_gateway(verb)

            if parallel_gateway:
                triggers.insert(len(triggers) - 1, {"category": "parallel_gateway", "verb": verb})
                triggers.append({"category": "sequence_flow_change", "verb": verb})

            sequence_flow_change = detect_sequence_flow_change(verb)

            if sequence_flow_change:
                triggers.append({"category": "sequence_flow_change", "verb": verb})

            sequence_flow_join = detect_sequence_flow_join(doc, verb)

            if sequence_flow_join:
                triggers.append({"category": "sequence_flow_join", "verb": verb})
                continue

            process_termination = detect_process_termination(verb)

            if process_termination:
                triggers.append({"category": "process_termination", "verb": verb})
                continue

            if has_children_verbs(verb):
                continue

            triggers.append({"category": "activity", "verb": verb})

    return triggers


def parse_triggers(triggers):
    elements = []

    predecessor = None
    open_gateways = {}

    for trigger in triggers:
        if trigger.get('category') == "activity":
            bpmn_element = {"category": "bpmn:Task", "identifier": "Task_" + str(trigger["verb"].idx), "value": trigger["verb"].lemma_, "actor": "Default", "predecessor": predecessor}
            elements.append(bpmn_element)
            predecessor = bpmn_element.get('identifier')
        elif trigger.get('category') == "exclusive_gateway":
            bpmn_element = {"category": "bpmn:ExclusiveGateway", "identifier": "ExclusiveGateway_" + str(trigger["verb"].idx), "value": "", "actor": "Default", "predecessor": predecessor}
            elements.append(bpmn_element)
            predecessor = bpmn_element.get('identifier')
            open_gateways[bpmn_element.get('identifier')] = []
        elif trigger.get('category') == "parallel_gateway":
            bpmn_element = {"category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_" + str(trigger["verb"].idx), "value": "", "actor": "Default", "predecessor": predecessor}
            elements.append(bpmn_element)
            predecessor = bpmn_element.get('identifier')
            open_gateways[bpmn_element.get('identifier')] = []
        elif trigger.get('category') == "sequence_flow_change":
            if not open_gateways:
                continue

            last_gateway = list(open_gateways)[-1]
            open_gateways[last_gateway].append(predecessor)
            predecessor = last_gateway
        elif trigger.get('category') == "sequence_flow_join":
            if not open_gateways:
                continue

            last_gateway = list(open_gateways)[-1]
            open_gateways[last_gateway].append(predecessor)

            if "ExclusiveGateway" in last_gateway:
                bpmn_element = {
                    "category": "bpmn:ExclusiveGateway", "identifier": "ExclusiveGateway_Join_" + str(trigger["verb"].idx), "value": "", "actor": "Default", "predecessors": open_gateways[last_gateway]
                }
            else:
                bpmn_element = {
                    "category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_Join_" + str(trigger["verb"].idx), "value": "", "actor": "Default", "predecessors": open_gateways[last_gateway]
                }

            elements.append(bpmn_element)
            predecessor = bpmn_element.get('identifier')
            open_gateways.pop(last_gateway)
        elif trigger.get('category') == "process_termination":
            if open_gateways:
                last_gateway = list(open_gateways)[-1]

                if "ParallelGateway" in last_gateway:
                    open_gateways[last_gateway].append(predecessor)

                    bpmn_element = {
                        "category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_Join_" + str(trigger["verb"].idx), "value": "", "actor": "Default",
                        "predecessors": open_gateways[last_gateway]
                    }

                    elements.append(bpmn_element)
                    predecessor = bpmn_element.get('identifier')

                bpmn_element = {"category": "bpmn:EndEvent", "identifier": "EndEvent_" + str(trigger["verb"].idx), "value": trigger["verb"].lemma_, "actor": "Default", "predecessor": predecessor}
                elements.append(bpmn_element)

                open_gateways.pop(last_gateway)
                predecessor = last_gateway
            else:
                bpmn_element = {"category": "bpmn:EndEvent", "identifier": "EndEvent_" + str(trigger["verb"].idx), "value": trigger["verb"].lemma_, "actor": "Default", "predecessor": predecessor}
                elements.append(bpmn_element)

            for gateway in list(open_gateways):
                if not open_gateways[gateway]:
                    open_gateways.pop(gateway)
                    predecessor = gateway

    if open_gateways:
        for gateway in list(open_gateways):
            if gateway == list(open_gateways)[-1]:
                open_gateways[gateway].append(predecessor)

            if "ExclusiveGateway" in gateway:
                for last_element in open_gateways[gateway]:
                    bpmn_element = next(element for element in elements if element["identifier"] == last_element)

                    end_event_element = {
                        "category": "bpmn:EndEvent", "identifier": "EndEvent_" + bpmn_element.get('identifier'), "value": bpmn_element.get('value'),
                        "actor": bpmn_element.get('actor'), "predecessor": bpmn_element.get('identifier')
                    }
                    elements.insert(elements.index(bpmn_element) + 1, end_event_element)
            else:
                bpmn_element = next(element for element in elements if element["identifier"] in open_gateways[gateway])

                parallel_gateway_join = {
                    "category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_Join_" + bpmn_element.get('identifier'), "value": "",
                    "actor": bpmn_element.get('actor'), "predecessors": open_gateways[gateway]
                }

                elements.append(parallel_gateway_join)
                end_event_element = {
                    "category": "bpmn:EndEvent", "identifier": "EndEvent_" + parallel_gateway_join.get('identifier'), "value": "",
                    "actor": bpmn_element.get('actor'), "predecessor": parallel_gateway_join.get('identifier')
                }
                elements.append(end_event_element)

            open_gateways.pop(gateway)

    return elements


def get_parent_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "xcomp")), None)


def get_conjunct_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "conj")), None)


def has_children_verbs(verb):
    verbs = list(child for child in verb.children if (child.dep_ == "xcomp"))

    if verbs:
        return True
    else:
        return False


def detect_exclusive_gateway(verb):
    parent_verb = get_parent_verb(verb)

    if parent_verb:
        return detect_exclusive_gateway(parent_verb)

    conjunct_verb = get_conjunct_verb(verb)

    if conjunct_verb:
        return detect_exclusive_gateway(conjunct_verb)

    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in exclusive_markers)), None)

    if mark:
        return verb

    if verb == verb.sent.root:
        return None

    marker_phrase = get_marker_phrase(verb.sent.root)

    if marker_phrase in exclusive_markers:
        return verb

    return None


def detect_parallel_gateway(verb):
    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in parallel_markers)), None)

    if mark:
        return verb

    marker_phrase = get_marker_phrase(verb)

    if marker_phrase in parallel_markers:
        return verb

    return None


def detect_sequence_flow_change(verb):
    advmod = next((child for child in verb.children if (child.dep_ == "advmod" and child.text.lower() in sequence_flow_change_markers)), None)

    if advmod:
        return verb

    marker_phrase = get_marker_phrase(verb)

    if marker_phrase in sequence_flow_change_markers:
        return verb

    return None


def detect_sequence_flow_join(doc, verb):
    nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass" and child.text.lower() in sequence_flow_join_markers)), None)

    if verb.lemma_ in sequence_flow_join_verbs and nsubjpass:
        return verb

    if verb.lemma_ in sequence_flow_join_verbs and doc[verb.sent.start] in verb.children:
        if any(marker for marker in sequence_flow_join_markers if marker in doc[verb.sent.start:verb.i].text.lower()):
            return verb

    return None


def detect_process_termination(verb):
    has_marker = any(child for child in verb.children if (child.dep_ == "nsubj" and child.text.lower() in process_termination_markers))
    has_verb = (verb.lemma_ in process_termination_verbs)

    if has_marker and has_verb:
        return verb

    return None


def get_marker_phrase(verb):
    prep = next((child for child in verb.children if (child.dep_ == "prep")), None)

    if prep:
        pobj = next((child for child in prep.children if (child.dep_ == "pobj")), None)

        if pobj:
            return (prep.text + " " + pobj.text).lower()

    return None
