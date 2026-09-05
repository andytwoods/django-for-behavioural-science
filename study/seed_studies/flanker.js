// Minimal Flanker task: respond to the CENTRE arrow (f = left, j = right).
// This is a jsPsych timeline. Paste it into a new study's "code" field in the admin,
// or let the seed migration load it for you.
const fixation = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: '<p style="font-size:48px;">+</p>',
  choices: "NO_KEYS",
  trial_duration: 500
};

const flanker = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: jsPsych.timelineVariable('stimulus'),
  choices: ['f', 'j'],
  data: {
    condition: jsPsych.timelineVariable('condition'),
    correct_response: jsPsych.timelineVariable('correct_response')
  },
  on_finish: function (data) {
    data.correct = jsPsych.pluginAPI.compareKeys(data.response, data.correct_response);
  }
};

const instructions = {
  type: jsPsychHtmlKeyboardResponse,
  stimulus: '<p>Press <b>f</b> if the CENTRE arrow points left, <b>j</b> if it points right.</p>' +
            '<p>Press any key to begin.</p>'
};

timeline.push(instructions);
timeline.push({
  timeline: [fixation, flanker],
  timeline_variables: [
    { stimulus: '<p style="font-size:48px;letter-spacing:8px;">&lt;&lt;&lt;&lt;&lt;</p>', condition: 'congruent',   correct_response: 'f' },
    { stimulus: '<p style="font-size:48px;letter-spacing:8px;">&gt;&gt;&gt;&gt;&gt;</p>', condition: 'congruent',   correct_response: 'j' },
    { stimulus: '<p style="font-size:48px;letter-spacing:8px;">&gt;&gt;&lt;&gt;&gt;</p>', condition: 'incongruent', correct_response: 'f' },
    { stimulus: '<p style="font-size:48px;letter-spacing:8px;">&lt;&lt;&gt;&lt;&lt;</p>', condition: 'incongruent', correct_response: 'j' }
  ],
  randomize_order: true,
  repetitions: 2
});
