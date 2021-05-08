import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

exclusive_markers = ["if", "in case", "in the case", "for the case"]
parallel_markers = ["at the same time", "whereas", "while"]
sequence_flow_change_markers = ["otherwise", "in the other case"]
sequence_flow_join_markers = ["the sequence flow", "the flow", "once one of these activities", "once these activities", "after each of these activities", "after these activities"]
sequence_flow_join_verbs = ["merge", "perform", "complete", "execute"]
process_termination_markers = ["the business process", "this business process", "the process", "this process"]
process_termination_verbs = ["end", "finish", "stop", "terminate"]
intermediate_event_markers = ["once", "after"]
ignored_conditional_phrases = ["if", "in case", "that", "for the case"]
ignored_prepositional_phrases = ["at the same time", "in addition", "in case", "in the case", "in the other case", "for the case"]
stopwords = ["a", "an", "the", "she", "her", "he", "his"]


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    triggers = get_triggers(doc)
    elements = get_elements(doc, triggers)

    svg = displacy.render(doc, style="dep")

    output_path = Path("./dependency_plot.svg")
    output_path.open("w", encoding="utf-8").write(svg)

    return elements


def get_triggers(doc):
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

            intermediate_event = detect_intermediate_event(verb)

            if intermediate_event:
                triggers.append({"category": "intermediate_event", "verb": verb})
                continue

            if has_children_verbs(verb):
                continue

            business_object = get_business_object(verb)

            if business_object:
                triggers.append({"category": "task", "verb": verb})
                continue

    if len(triggers) > 0:
        triggers[0]["category"] = "start_event"

    return triggers


def get_elements(doc, triggers):
    elements = []

    actor = "Default"
    predecessor = None
    open_gateways = {}

    for trigger in triggers:
        if trigger == triggers[0] or trigger.get('category') in ["task", "intermediate_event", "start_event"]:
            new_actor = get_actor_label(trigger["verb"])
            if new_actor:
                actor = new_actor
        if trigger.get('category') == "start_event":
            element = {"category": "bpmn:StartEvent", "identifier": str(trigger["verb"].i), "value": get_event_label(trigger["verb"]), "actor": actor, "predecessor": predecessor}
            elements.append(element)
            predecessor = element.get('identifier')
        elif trigger.get('category') == "task":
            element = {"category": "bpmn:Task", "identifier": str(trigger["verb"].i), "value": get_task_label(trigger["verb"]), "actor": actor, "predecessor": predecessor}
            elements.append(element)
            predecessor = element.get('identifier')
        elif trigger.get('category') == "intermediate_event":
            element = {"category": "bpmn:IntermediateThrowEvent", "identifier": str(trigger["verb"].i), "value": get_event_label(trigger["verb"]), "actor": actor, "predecessor": predecessor}
            elements.append(element)
            predecessor = element.get('identifier')
        elif trigger.get('category') == "exclusive_gateway":
            element = {
                "category": "bpmn:ExclusiveGateway", "identifier": "ExclusiveGateway_" + str(trigger["verb"].i),
                "value": get_conditional_label(doc, trigger["verb"]), "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get('identifier')
            open_gateways[element.get('identifier')] = []
        elif trigger.get('category') == "parallel_gateway":
            element = {"category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_" + str(trigger["verb"].i), "value": "", "actor": actor, "predecessor": predecessor}
            elements.append(element)
            predecessor = element.get('identifier')
            open_gateways[element.get('identifier')] = []
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
                category = "bpmn:ExclusiveGateway"
            else:
                category = "bpmn:ParallelGateway"

            element = {"category": category, "identifier": last_gateway + "_Join", "value": "", "actor": actor, "predecessors": open_gateways[last_gateway]}
            elements.append(element)
            predecessor = element.get('identifier')
            open_gateways.pop(last_gateway)
        elif trigger.get('category') == "process_termination":
            if open_gateways:
                last_gateway = list(open_gateways)[-1]

                if "ParallelGateway" in last_gateway:
                    open_gateways[last_gateway].append(predecessor)

                    element = {"category": "bpmn:ParallelGateway", "identifier": last_gateway + "_Join", "value": "", "actor": actor, "predecessors": open_gateways[last_gateway]}
                    elements.append(element)
                    predecessor = element.get('identifier')
                    element = {"category": "bpmn:EndEvent", "identifier": str(trigger["verb"].i), "value": "Process terminated", "actor": actor, "predecessor": predecessor}
                else:
                    element = {"category": "bpmn:EndEvent", "identifier": str(trigger["verb"].i), "value": get_event_label(doc[int(predecessor)]), "actor": actor, "predecessor": predecessor}

                elements.append(element)
                predecessor = last_gateway
                open_gateways.pop(last_gateway)
            else:
                element = {"category": "bpmn:EndEvent", "identifier": str(trigger["verb"].i), "value": get_event_label(doc[int(predecessor)]), "actor": actor, "predecessor": predecessor}
                elements.append(element)

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
                    element = next(element for element in elements if element["identifier"] == last_element)

                    end_event_element = {
                        "category": "bpmn:EndEvent", "identifier": "EndEvent_" + element.get('identifier'), "value": get_event_label(doc[int(element.get('identifier'))]),
                        "actor": element.get('actor'), "predecessor": element.get('identifier')
                    }
                    elements.insert(elements.index(element) + 1, end_event_element)
            else:
                element = next(element for element in elements if element["identifier"] in open_gateways[gateway])

                parallel_gateway_join = {
                    "category": "bpmn:ParallelGateway", "identifier": gateway + "_Join", "value": "", "actor": element.get('actor'), "predecessors": open_gateways[gateway]
                }
                elements.append(parallel_gateway_join)

                end_event_element = {
                    "category": "bpmn:EndEvent", "identifier": "EndEvent_" + parallel_gateway_join.get('identifier'), "value": "Process terminated",
                    "actor": element.get('actor'), "predecessor": parallel_gateway_join.get('identifier')
                }
                elements.append(end_event_element)

            open_gateways.pop(gateway)

    return elements


def get_parent_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "xcomp")), None)


def get_conjunct_children_verb(verb):
    return next((child for child in verb.children if (child.dep_ == "conj")), None)


def get_conjunct_parent_verb(verb):
    return next((ancestor for ancestor in verb.ancestors if (verb in ancestor.children and verb.dep_ == "conj")), None)


def get_verb_particle(verb):
    return next((child for child in verb.children if (child.dep_ == "prt")), None)


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

    conjunct_parent_verb = get_conjunct_parent_verb(verb)

    if conjunct_parent_verb:
        return detect_exclusive_gateway(conjunct_parent_verb)

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


def detect_intermediate_event(verb):
    has_marker = any(child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in intermediate_event_markers))

    if has_marker:
        return verb

    return None


def get_marker_phrase(verb):
    prep = next((child for child in verb.children if (child.dep_ == "prep")), None)

    if prep:
        pobj = next((child for child in prep.children if (child.dep_ == "pobj")), None)

        if pobj:
            return (prep.text + " " + pobj.text).lower()

    return None


def get_event_label(verb):
    business_object = get_business_object(verb)

    if business_object:
        verb_particle = get_verb_particle(verb)

        if verb_particle:
            return clean_label(business_object + " " + verb._.inflect("VBN") + " " + verb_particle.text)

        return clean_label(business_object + " " + verb._.inflect("VBN"))

    return None


def get_task_label(verb):
    business_object = get_business_object(verb)

    if business_object:
        verb_particle = get_verb_particle(verb)

        if verb_particle:
            return clean_label(verb.lemma_ + " " + verb_particle.text + " " + business_object)

        return clean_label(verb.lemma_ + " " + business_object)

    return clean_label(verb.lemma_)


def get_conditional_label(doc, verb):
    text = doc[verb.left_edge.i:verb.right_edge.i + 1].text.lower()

    for phrase in ignored_conditional_phrases:
        text = text.replace(phrase, "")

    return clean_label(text + "?")


def get_actor_label(verb):
    if is_passive_verb(verb):
        agent = next((child for child in verb.children if (child.dep_ == "agent")), None)

        if agent:
            actor = next((child for child in agent.children if (child.dep_ == "pobj")), None)

            if actor:
                return clean_actor_label(actor.text)

        conjunct_children_verb = get_conjunct_children_verb(verb)

        if conjunct_children_verb:
            return get_actor_label(conjunct_children_verb)
    else:
        actor = next((child for child in verb.children if (child.dep_ == "nsubj")), None)

        if actor:
            return clean_actor_label(actor.text)

        conjunct_parent_verb = get_conjunct_parent_verb(verb)

        if conjunct_parent_verb:
            return get_actor_label(conjunct_parent_verb)

    return None


def get_business_object(verb):
    if is_passive_verb(verb):
        parent_verb = get_parent_verb(verb)

        if parent_verb:
            return get_business_object(parent_verb)

        label = next((child for child in verb.children if (child.dep_ == "nsubjpass")), None)

        if label:
            prepositional_phrase = get_prepositional_phrase(verb)

            if prepositional_phrase:
                return label.text + " " + prepositional_phrase

            return label.text

        conjunct_parent_verb = get_conjunct_parent_verb(verb)

        if conjunct_parent_verb:
            return get_business_object(conjunct_parent_verb)
    else:
        if has_children_verbs(verb):
            label = next((child for child in verb.children if (child.dep_ == "nsubj")), None)

            if label:
                return label.text
        else:
            label = next((child for child in verb.children if (child.dep_ == "dobj")), None)

            if label:
                prepositional_phrase = get_prepositional_phrase(verb)

                if prepositional_phrase:
                    return label.text + " " + prepositional_phrase

                return label.text

            conjunct_children_verb = get_conjunct_children_verb(verb)

            if conjunct_children_verb:
                return get_business_object(conjunct_children_verb)

            parent_verb = get_parent_verb(verb)

            if parent_verb:
                return get_business_object(parent_verb)

    prepositional_phrase = get_prepositional_phrase(verb)

    if prepositional_phrase:
        return prepositional_phrase

    return None


def get_prepositional_phrase(verb):
    prepositions = list(child for child in verb.children if (child.dep_ == "prep"))
    prepositional_phrase = ""

    while prepositions:
        for preposition in prepositions:
            pobj = next((child for child in preposition.children if (child.dep_ == "pobj")), None)

            if pobj:
                text = preposition.text + " " + pobj.text

                if not any(phrase for phrase in ignored_prepositional_phrases if phrase in text.lower()):
                    prepositional_phrase += text + " "
                    prepositions.extend(list(child for child in pobj.children if (child.dep_ == "prep")))

            prepositions.remove(preposition)

    if not prepositional_phrase:
        return None
    else:
        return prepositional_phrase.strip()


def is_passive_verb(verb):
    conjunct_parent_verb = get_conjunct_parent_verb(verb)

    if conjunct_parent_verb:
        return is_passive_verb(conjunct_parent_verb)

    has_auxpass = any(child for child in verb.children if (child.dep_ == "auxpass"))
    has_nsubjpass = any(child for child in verb.children if (child.dep_ == "nsubjpass"))

    if has_auxpass and has_nsubjpass:
        return True

    if has_auxpass and get_parent_verb(verb):
        return True

    return False


def clean_label(label):
    return (" ".join([word for word in label.split() if word.lower() not in stopwords])).capitalize()


def clean_actor_label(label):
    label = (" ".join([word for word in label.split() if word.lower() not in stopwords]))

    if label.isupper():
        return label

    return label.title()
