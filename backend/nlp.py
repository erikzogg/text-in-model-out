import spacy
import lemminflect
from spacy import displacy
from pathlib import Path

split_exclusive_gateway_indicators = [
    "for the case", "if", "in case", "in the case"
]

split_parallel_gateway_indicators = [
    "at the same time", "whereas", "while"
]

sequence_flow_change_indicators = [
    "in the other case", "otherwise"
]

join_gateway_indicators = [
    "after each of these activities", "after each of these tasks", "after these activities",
    "after these tasks", "once these activities", "once these tasks",
    "once one of these activities", "once one of these tasks", "the flow", "the sequence flow"
]

join_gateway_verbs = [
    "complete", "execute", "merge", "perform"
]

end_event_indicators = [
    "the business process", "this business process", "the process", "this process"
]

end_event_verbs = [
    "end", "finish", "stop", "terminate"
]

intermediate_event_indicators = [
    "after", "once"
]

ignored_conditional_phrases = [
    "if", "that"
]

ignored_prepositional_phrases = [
    "at the same time", "in addition", "in case", "in the case", "in that case",
    "in the other case", "in this case", "for the case"
]

stopwords = [
    "a", "an", "he", "her", "his", "she", "the", "they", "their"
]


def parse(text):
    nlp = spacy.load("en_core_web_trf")
    nlp.add_pipe("merge_noun_chunks")

    doc = nlp(text)

    return get_bpmn_elements(doc, get_process_elements(doc))


def get_process_elements(doc):
    elements = []

    for sent in doc.sents:
        verbs = [token for token in sent if token.pos_ == "VERB"]

        for verb in verbs:
            split_exclusive_gateway = detect_split_exclusive_gateway(verb)

            if split_exclusive_gateway:
                if split_exclusive_gateway == verb:
                    elements.append({"category": "split_exclusive_gateway", "verb": verb})

                continue

            split_parallel_gateway = detect_split_parallel_gateway(verb)

            if split_parallel_gateway:
                elements.insert(len(elements) - 1, {"category": "split_parallel_gateway", "verb": verb})
                elements.append({"category": "sequence_flow_change", "verb": verb})

            sequence_flow_change = detect_sequence_flow_change(verb)

            if sequence_flow_change:
                elements.append({"category": "sequence_flow_change", "verb": verb})

            join_gateway = detect_join_gateway(doc, verb)

            if join_gateway:
                elements.append({"category": "join_gateway", "verb": verb})
                continue

            end_event = detect_end_event(verb)

            if end_event:
                elements.append({"category": "end_event", "verb": verb})
                continue

            intermediate_event = detect_intermediate_event(verb)

            if intermediate_event:
                elements.append({"category": "intermediate_event", "verb": verb})
                continue

            if has_children_verbs(verb):
                continue

            business_object = get_business_object(verb)

            if business_object:
                elements.append({"category": "task", "verb": verb})
                continue

    if len(elements) > 0:
        elements[0]["category"] = "start_event"

    return elements


def get_bpmn_elements(doc, process_elements):
    elements = []

    actor = "Default"
    predecessor = None
    open_gateways = {}

    for process_element in process_elements:
        if process_element == process_elements[0] or process_element.get("category") in ["task", "intermediate_event", "start_event"]:
            new_actor = get_actor_label(process_element["verb"])
            if new_actor:
                actor = new_actor
        if process_element.get("category") == "start_event":
            element = {
                "category": "bpmn:StartEvent", "identifier": str(process_element["verb"].i),
                "value": get_event_label(process_element["verb"]), "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get("identifier")
        elif process_element.get("category") == "task":
            element = {
                "category": "bpmn:Task", "identifier": str(process_element["verb"].i),
                "value": get_task_label(process_element["verb"]), "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get("identifier")
        elif process_element.get("category") == "intermediate_event":
            element = {
                "category": "bpmn:IntermediateThrowEvent", "identifier": str(process_element["verb"].i),
                "value": get_event_label(process_element["verb"]), "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get("identifier")
        elif process_element.get("category") == "split_exclusive_gateway":
            element = {
                "category": "bpmn:ExclusiveGateway", "identifier": "ExclusiveGateway_" + str(process_element["verb"].i),
                "value": get_conditional_label(doc, process_element["verb"]), "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get("identifier")
            open_gateways[element.get("identifier")] = []
        elif process_element.get("category") == "split_parallel_gateway":
            element = {
                "category": "bpmn:ParallelGateway", "identifier": "ParallelGateway_" + str(process_element["verb"].i),
                "value": "", "actor": actor, "predecessor": predecessor
            }
            elements.append(element)
            predecessor = element.get("identifier")
            open_gateways[element.get("identifier")] = []
        elif process_element.get("category") == "sequence_flow_change":
            if not open_gateways:
                continue

            last_gateway = list(open_gateways)[-1]
            open_gateways[last_gateway].append(predecessor)
            predecessor = last_gateway
        elif process_element.get("category") == "join_gateway":
            if not open_gateways:
                continue

            last_gateway = list(open_gateways)[-1]
            open_gateways[last_gateway].append(predecessor)

            if "ExclusiveGateway" in last_gateway:
                category = "bpmn:ExclusiveGateway"
            else:
                category = "bpmn:ParallelGateway"

            element = {
                "category": category, "identifier": last_gateway + "_Join",
                "value": "", "actor": actor, "predecessors": open_gateways[last_gateway]
            }
            elements.append(element)
            predecessor = element.get("identifier")
            open_gateways.pop(last_gateway)
        elif process_element.get("category") == "end_event":
            if open_gateways:
                last_gateway = list(open_gateways)[-1]

                if "ParallelGateway" in last_gateway:
                    open_gateways[last_gateway].append(predecessor)

                    element = {
                        "category": "bpmn:ParallelGateway", "identifier": last_gateway + "_Join",
                        "value": "", "actor": actor, "predecessors": open_gateways[last_gateway]
                    }
                    elements.append(element)
                    predecessor = element.get("identifier")
                    element = {
                        "category": "bpmn:EndEvent", "identifier": str(process_element["verb"].i),
                        "value": "Process terminated", "actor": actor, "predecessor": predecessor
                    }
                else:
                    for last_element in open_gateways[last_gateway]:
                        element = next(element for element in elements if element["identifier"] == last_element)

                        if "Gateway" not in element.get("identifier"):
                            value = get_event_label(doc[int(element.get("identifier"))])
                        else:
                            value = "Process terminated"

                        end_event_element = {
                            "category": "bpmn:EndEvent", "identifier": "EndEvent_" + element.get("identifier"),
                            "value": value, "actor": element.get("actor"), "predecessor": element.get("identifier")
                        }
                        elements.insert(elements.index(element) + 1, end_event_element)

                    element = {
                        "category": "bpmn:EndEvent", "identifier": str(process_element["verb"].i),
                        "value": get_event_label(doc[int(predecessor)]), "actor": actor, "predecessor": predecessor
                    }

                elements.append(element)
                predecessor = last_gateway
                open_gateways.pop(last_gateway)
            else:
                if "Gateway" not in predecessor:
                    value = get_event_label(doc[int(predecessor)])
                else:
                    value = "Process terminated"

                element = {
                    "category": "bpmn:EndEvent", "identifier": str(process_element["verb"].i),
                    "value": value, "actor": actor, "predecessor": predecessor
                }
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

                    if "Gateway" not in element.get("identifier"):
                        value = get_event_label(doc[int(element.get("identifier"))])
                    else:
                        value = "Process terminated"

                    end_event_element = {
                        "category": "bpmn:EndEvent", "identifier": "EndEvent_" + element.get("identifier"),
                        "value": value, "actor": element.get("actor"), "predecessor": element.get("identifier")
                    }
                    elements.insert(elements.index(element) + 1, end_event_element)
            else:
                element = next(element for element in elements if element["identifier"] in open_gateways[gateway])

                parallel_gateway_join = {
                    "category": "bpmn:ParallelGateway", "identifier": gateway + "_Join",
                    "value": "", "actor": element.get("actor"), "predecessors": open_gateways[gateway]
                }
                elements.append(parallel_gateway_join)

                end_event_element = {
                    "category": "bpmn:EndEvent", "identifier": "EndEvent_" + parallel_gateway_join.get("identifier"),
                    "value": "Process terminated", "actor": element.get("actor"),
                    "predecessor": parallel_gateway_join.get("identifier")
                }
                elements.append(end_event_element)

            open_gateways.pop(gateway)

    if len(elements) > 0:
        if elements[-1].get("category") != "bpmn:EndEvent":
            if "Gateway" not in predecessor:
                value = get_event_label(doc[int(predecessor)])
            else:
                value = "Process terminated"

            elements.append({
                "category": "bpmn:EndEvent", "identifier": "EndEvent_" + predecessor,
                "value": value, "actor": actor, "predecessor": predecessor
            })

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


def detect_split_exclusive_gateway(verb):
    parent_verb = get_parent_verb(verb)

    if parent_verb:
        return detect_split_exclusive_gateway(parent_verb)

    conjunct_parent_verb = get_conjunct_parent_verb(verb)

    if conjunct_parent_verb:
        return detect_split_exclusive_gateway(conjunct_parent_verb)

    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in split_exclusive_gateway_indicators)), None)

    if mark:
        return verb

    if verb == verb.sent.root:
        return None

    indicator_phrase = get_indicator_phrase(verb.sent.root)

    if indicator_phrase in split_exclusive_gateway_indicators:
        return verb

    return None


def detect_split_parallel_gateway(verb):
    mark = next((child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in split_parallel_gateway_indicators)), None)

    if mark:
        return verb

    indicator_phrase = get_indicator_phrase(verb)

    if indicator_phrase in split_parallel_gateway_indicators:
        return verb

    return None


def detect_sequence_flow_change(verb):
    advmod = next((child for child in verb.children if (child.dep_ == "advmod" and child.text.lower() in sequence_flow_change_indicators)), None)

    if advmod:
        return verb

    indicator_phrase = get_indicator_phrase(verb)

    if indicator_phrase in sequence_flow_change_indicators:
        return verb

    return None


def detect_join_gateway(doc, verb):
    nsubjpass = next((child for child in verb.children if (child.dep_ == "nsubjpass" and child.text.lower() in join_gateway_indicators)), None)

    if verb.lemma_ in join_gateway_verbs and nsubjpass:
        return verb

    if verb.lemma_ in join_gateway_verbs and doc[verb.sent.start] in verb.children:
        if any(indicator for indicator in join_gateway_indicators if indicator in doc[verb.sent.start:verb.i].text.lower()):
            return verb

    return None


def detect_end_event(verb):
    has_indicator = any(child for child in verb.children if (child.dep_ == "nsubj" and child.text.lower() in end_event_indicators))
    has_verb = (verb.lemma_ in end_event_verbs)

    if has_indicator and has_verb:
        return verb

    return None


def detect_intermediate_event(verb):
    has_indicator = any(child for child in verb.children if (child.dep_ == "mark" and child.text.lower() in intermediate_event_indicators))

    if has_indicator:
        return verb

    return None


def get_indicator_phrase(verb):
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
            prepositional_phrase_verb = get_prepositional_phrase(verb)
            prepositional_phrase_label = get_prepositional_phrase(label)

            if prepositional_phrase_verb and prepositional_phrase_label:
                return label.text + " " + prepositional_phrase_label + " " + prepositional_phrase_verb

            if prepositional_phrase_verb:
                return label.text + " " + prepositional_phrase_verb

            if prepositional_phrase_label:
                return label.text + " " + prepositional_phrase_label

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
                prepositional_phrase_verb = get_prepositional_phrase(verb)
                prepositional_phrase_label = get_prepositional_phrase(label)

                if prepositional_phrase_verb and prepositional_phrase_label:
                    return label.text + " " + prepositional_phrase_label + " " + prepositional_phrase_verb

                if prepositional_phrase_verb:
                    return label.text + " " + prepositional_phrase_verb

                if prepositional_phrase_label:
                    return label.text + " " + prepositional_phrase_label

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


def get_prepositional_phrase(token):
    prepositions = list(child for child in token.children if (child.dep_ == "prep"))
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
