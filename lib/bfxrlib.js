/*! bfxrlib — standalone sound synthesis
MIT License

Copyright (c) 2021 Stephen Lavelle

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Includes SfxrSynth-derived DSP, Copyright 2010 Thomas Vian, Apache License 2.0.
Modified for Bfxr/Bfxr2 by Stephen Lavelle.

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "[]"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright [yyyy] [name of copyright owner]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

Includes Adventure Kid Waveforms (CC0), converted by Brad Roy.
https://www.adventurekid.se/akrt/waveforms/adventure-kid-waveforms/
*/
(function(global) {
"use strict";
// Keep existing seeded generators private, including Math.clamp and Math.random.
const Math = Object.create(global.Math);
const SAMPLE_RATE = 44100, CONVERSION_FACTOR = 2 * Math.PI / SAMPLE_RATE;
// js/globals.js
Math.clamp = function(value, min, max){
    return Math.max(min, Math.min(value, max));
}

const SYNTH_DISPLAY_NAMES = {
    Transfxr:'Transfxr', Clonkr:'Tangs', Machinr:'Motors',
    Jinglr:'Jingles', Squishr:'Squishy', Mixr:'Mixfxr',
    Crittr:'Beasts', Birdr:'Bird', Signlr:'Signal',
    Fractr:'Cracker', Riftr:'Sonar', Swarmr:'Swarms',
    Rustlr:'Rustler', Boomr:'Boomer', Zappr:'Zapper',
    Whooshr:'Whoosh', Bouncr:'Bonks', Breathr:'Breath',
    Choirr:'Choir', Pluckr:'Plucked', Glitchr:'Glitches'
};

function synth_display_name(name) {
    return SYNTH_DISPLAY_NAMES[name] || name;
}

// shallow copy
function copy_obj(obj){
    return Object.assign({}, obj);
}

function step(n){
    return function(x){
        if (x<=0 || x>=1) return 0;
        return ((x*x*x)*n-x*n)*(1-x)*(-1.5);
    }
}

function resize_fn(fn,a1,a2,b1,b2){
    return function(y){
        return fn( (y-b1)/(b2-b1) * (a2-a1) + a1 );
    }
}

function add_fns( ...fns ){
    return function(x){
        return fns.reduce((acc,fn) => acc + fn(x), 0);
    }
}

function isVisible (ele, container) {
    const eleTop = ele.offsetTop;
    const eleBottom = eleTop + ele.clientHeight;

    const containerTop = container.scrollTop;
    const containerBottom = containerTop + container.clientHeight;

    // The element is fully visible in the container
    return (
        (eleTop >= containerTop && eleBottom <= containerBottom) ||
        // Some part of the element is visible in the container
        (eleTop < containerTop && containerTop < eleBottom) ||
        (eleTop < containerBottom && containerBottom < eleBottom)
    );
};

function setVisible (ele, container) {
    if (isVisible(ele, container)){
        return;
    }
    //if above
    if (ele.offsetTop < container.scrollTop){
        container.scrollTop = ele.offsetTop;
    }
    //if below
    else if (ele.offsetTop + ele.offsetHeight > container.scrollTop + container.offsetHeight){
        container.scrollTop = ele.offsetTop - container.offsetHeight + ele.offsetHeight;
    }
}

function lerp(a, b, t){
    return a + t * (b - a);
}

// js/synths/templates.js
const TEMPLATES_JSON = {
  "Bfxr": {
    "pickup_coin": {
      "Coin": {
        "masterVolume": [
          0.85185
        ],
        "waveType": [
          0
        ],
        "attackTime": [
          0
        ],
        "sustainTime": [
          0.016874472672728978,
          0.10333
        ],
        "sustainPunch": [
          0.30333,
          0.60333
        ],
        "decayTime": [
          0.16312552732727104,
          0.50333
        ],
        "compressionAmount": [
          0
        ],
        "frequency_start": [
          0.4,
          0.9
        ],
        "min_frequency_relative_to_starting_frequency": [
          0
        ],
        "frequency_slide": [
          0
        ],
        "frequency_acceleration": [
          0
        ],
        "vibratoDepth": [
          0
        ],
        "vibratoSpeed": [
          0
        ],
        "overtones": [
          0
        ],
        "overtoneFalloff": [
          0
        ],
        "pitch_jump_repeat_speed": [
          0
        ],
        "pitch_jump_amount": [
          0
        ],
        "pitch_jump_onset_percent": [
          0
        ],
        "pitch_jump_2_amount": [
          0
        ],
        "pitch_jump_onset2_percent": [
          0
        ],
        "squareDuty": [
          0
        ],
        "dutySweep": [
          0
        ],
        "repeatSpeed": [
          0
        ],
        "flangerOffset": [
          0
        ],
        "flangerSweep": [
          0
        ],
        "lpFilterCutoff": [
          1
        ],
        "lpFilterCutoffSweep": [
          0
        ],
        "lpFilterResonance": [
          0
        ],
        "hpFilterCutoff": [
          0
        ],
        "hpFilterCutoffSweep": [
          0
        ],
        "bitCrush": [
          0
        ],
        "bitCrushSweep": [
          0
        ]
      },
      "Coin2": {
        "masterVolume": [
          0.85185
        ],
        "waveType": [
          0,
          2,
          4,
          1,
          7,
          11,
          5,
          10
        ],
        "attackTime": [
          0
        ],
        "sustainTime": [
          0.016874472672728978,
          0.10333
        ],
        "sustainPunch": [
          0.30333,
          0.60333
        ],
        "decayTime": [
          0.16312552732727104,
          0.50333
        ],
        "compressionAmount": [
          0
        ],
        "frequency_start": [
          0.4,
          0.9
        ],
        "min_frequency_relative_to_starting_frequency": [
          0
        ],
        "frequency_slide": [
          0,
          0.05333
        ],
        "frequency_acceleration": [
          0,
          0.09333
        ],
        "vibratoDepth": [
          0
        ],
        "vibratoSpeed": [
          0
        ],
        "overtones": [
          0
        ],
        "overtoneFalloff": [
          0
        ],
        "pitch_jump_repeat_speed": [
          0
        ],
        "pitch_jump_amount": [
          0.34667,
          0.38667
        ],
        "pitch_jump_onset_percent": [
          0.32667,
          0.29333
        ],
        "pitch_jump_2_amount": [
          0
        ],
        "pitch_jump_onset2_percent": [
          0
        ],
        "squareDuty": [
          0
        ],
        "dutySweep": [
          0
        ],
        "repeatSpeed": [
          0
        ],
        "flangerOffset": [
          0
        ],
        "flangerSweep": [
          0
        ],
        "lpFilterCutoff": [
          1
        ],
        "lpFilterCutoffSweep": [
          0
        ],
        "lpFilterResonance": [
          0
        ],
        "hpFilterCutoff": [
          0
        ],
        "hpFilterCutoffSweep": [
          0
        ],
        "bitCrush": [
          0
        ],
        "bitCrushSweep": [
          0
        ]
      }
    }
  }
};
// js/audio/AKWF.js
class AKWF {

    /* Adventure Kid Waveforms (AKWF) converted for use with Teensy Audio Library
*
*  Adventure Kid Waveforms(AKWF) Open waveforms library
*  https://www.adventurekid.se/akrt/waveforms/adventure-kid-waveforms/
*
*  This code is in the public domain, CC0 1.0 Universal (CC0 1.0)
*  https://creativecommons.org/publicdomain/zero/1.0/
*
*  Converted by Brad Roy, https://github.com/prosper00
*/

    /* AKWF_hvoice_0012 256 samples

    +-----------------------------------------------------------------------------------------------------------------+
    |          ***  **                                                                                                |
    |        ***     ***                                                                                              |
    |      ***         *                       *****                                    *******                       |
    |     **           **                     **   *****                              ***     **                      |
    |   **               *                  ***        ****                          **        **                     |
    | **                 **                **              ******                    *          **                    |
    |**                   *               **                    **                  **           **                   |
    |                     *              **                      ***               **             **                **|
    |                      *             *                          **            **               **             *** |
    |                      **           **                           **          *                  **          **    |
    |                       **          *                              *        **                   ***      ***     |
    |                        *        **                                ***   **                       ********       |
    |                        ***     **                                    ****                                       |
    |                          **   **                                                                                |
    |                           * ***                                                                                 |
    +-----------------------------------------------------------------------------------------------------------------+


    */

//suited for lower notes
    static hvoice_0012 = [
        33078, 34077, 35044, 36007, 36938, 37805, 38590, 39410, 40186, 40979, 41828, 42751, 43765, 44750, 45625, 46506,
        47377, 48459, 49580, 50412, 51254, 52132, 53054, 53969, 55064, 56224, 57157, 57762, 58474, 59326, 60025, 60421,
        60707, 60933, 61192, 61199, 60011, 57771, 55825, 55237, 55020, 53932, 51409, 48089, 45399, 44422, 44106, 42490,
        39350, 35232, 30729, 27122, 25230, 23798, 21402, 18034, 14910, 12701, 11362, 10543, 9717, 8561, 7008, 4596,
        1765, 131, 201, 1146, 2023, 2735, 3299, 3911, 5049, 7131, 9717, 11930, 13324, 14032, 14722, 16044,
        18235, 21043, 24261, 27245, 29408, 31047, 33083, 35737, 38158, 39841, 40886, 41556, 42213, 43245, 44552, 45917,
        47119, 47870, 48264, 48770, 49539, 49925, 49668, 49229, 48873, 48432, 47913, 47384, 46902, 46605, 46302, 45760,
        45142, 44704, 44318, 43802, 43332, 43042, 42636, 41996, 41337, 40780, 40348, 40072, 39783, 39377, 39035, 38729,
        38329, 37958, 37837, 37831, 37639, 37223, 36573, 35566, 34312, 33093, 32117, 31428, 30844, 30079, 29059, 27979,
        27098, 26276, 25428, 24454, 23049, 21274, 19381, 17785, 16557, 15675, 15000, 14446, 13983, 13647, 13422, 13168,
        12982, 12753, 12429, 12068, 11998, 12294, 12943, 13955, 15251, 16750, 18381, 20097, 21804, 23476, 25102, 26674,
        28171, 29696, 31260, 32930, 34804, 36952, 39192, 41282, 43127, 44699, 46099, 47372, 48514, 49476, 50175, 50618,
        50888, 51099, 51305, 51404, 51383, 51221, 50812, 50133, 49166, 47971, 46660, 45347, 44055, 42645, 40991, 39107,
        37176, 35376, 33764, 32251, 30646, 28956, 27272, 25659, 24192, 22866, 21633, 20368, 19107, 17971, 16966, 16123,
        15408, 14840, 14468, 14309, 14374, 14559, 14792, 14960, 15096, 15298, 15643, 16099, 16589, 17068, 17606, 18341,
        19312, 20471, 21661, 22740, 23624, 24392, 25151, 25945, 26715, 27439, 28051, 28700, 29403, 30342, 31272, 32180,
    ];


        /* AKWF_hvoice_0008 256 samples

  +-----------------------------------------------------------------------------------------------------------------+
  |     **  **                                                                                                      |
  |    **     **                                                                                                    |
  |   **       *                                                                                                    |
  |  **         *                                                                        **                         |
  |  *          **                                                                     *******                      |
  | **           **                                                                   **     ****                   |
  | *             *                                                                 ***          **                 |
  |*              **                                   ****                        **             **                |
  |*               *                             *******  ***                    ***                *               |
  |                 *                         ***           ***                ***                  **              |
  |                 **               **********               **              **                     **            *|
  |                  *             ***                         ***           **                       **           *|
  |                  **           **                             **         **                         **         * |
  |                   **       ***                                ***     ***                           ***      ** |
  |                    ** *****                                     *******                               ***   **  |
  +-----------------------------------------------------------------------------------------------------------------+


*/


//suited for higher notes
static hvoice_0008 = [
    33181, 35486, 37968, 40376, 42771, 45080, 47364, 49564, 51743, 53835, 55881, 57791, 59589, 61183, 62575, 63700,
    64584, 65156, 65464, 65532, 65397, 65033, 64481, 63756, 62857, 61795, 60589, 59244, 57769, 56187, 54493, 52700,
    50804, 48810, 46710, 44526, 42252, 39909, 37506, 35065, 32606, 30170, 27780, 25481, 23312, 21314, 19526, 17987,
    16727, 15759, 15085, 14680, 14507, 14529, 14701, 14981, 15335, 15729, 16131, 16520, 16883, 17220, 17530, 17823,
    18107, 18405, 18742, 19133, 19600, 20152, 20793, 21528, 22346, 23219, 24124, 25037, 25940, 26826, 27679, 28455,
    29125, 29658, 30037, 30271, 30376, 30375, 30291, 30150, 29969, 29778, 29596, 29441, 29340, 29318, 29391, 29570,
    29865, 30266, 30762, 31336, 31959, 32594, 33218, 33807, 34355, 34865, 35333, 35749, 36106, 36392, 36606, 36762,
    36877, 36973, 37079, 37206, 37368, 37560, 37770, 37977, 38155, 38274, 38317, 38275, 38137, 37905, 37573, 37132,
    36575, 35905, 35127, 34265, 33341, 32369, 31357, 30322, 29276, 28227, 27188, 26149, 25114, 24089, 23079, 22088,
    21128, 20203, 19329, 18525, 17801, 17168, 16639, 16221, 15920, 15747, 15693, 15744, 15903, 16162, 16516, 16965,
    17495, 18088, 18756, 19498, 20308, 21208, 22190, 23241, 24387, 25619, 26888, 28221, 29593, 30838, 31899, 32887,
    33833, 34687, 35481, 36256, 37010, 37776, 38593, 39464, 40400, 41413, 42484, 43599, 44747, 45894, 47011, 48063,
    48999, 49776, 50378, 50781, 50983, 50998, 50824, 50475, 49983, 49374, 48691, 47998, 47342, 46758, 46270, 45870,
    45527, 45218, 44900, 44544, 44118, 43587, 42913, 42071, 41043, 39822, 38423, 36863, 35174, 33393, 31568, 29740,
    27974, 26304, 24772, 23384, 22152, 21048, 20083, 19228, 18476, 17792, 17155, 16532, 15920, 15312, 14725, 14184,
    13722, 13384, 13196, 13215, 13436, 13915, 14619, 15604, 16811, 18301, 19969, 21884, 23902, 26136, 28375, 30869,
];




    /* AKWF_fmsynth_0012 256 samples

  +-----------------------------------------------------------------------------------------------------------------+
  |      *****                ******                                                 ***   **                       |
  |    ***                         ****                                            ***      **                      |
  |  ***                               ***                                        **         *                      |
  |***                                   ****                                   ***          **                     |
  |*                                        ****                              ***             *                     |
  |                                            ****                         ***               *                   **|
  |                                               ****                   ***                  **                 ** |
  |                                                  ******          *****                     *               ***  |
  |                                                       ***********                          *              **    |
  |                                                                                            **            **     |
  |                                                                                             *           **      |
  |                                                                                             *         **        |
  |                                                                                              *       **         |
  |                                                                                              **     **          |
  |                                                                                               *   ***           |
  +-----------------------------------------------------------------------------------------------------------------+


*/


    static fmsynth_0012 = [
        33063, 33949, 34766, 35596, 36388, 37173, 37929, 38666, 39379, 40067, 40731, 41364, 41976, 42552, 43106, 43625,
        44121, 44580, 45016, 45417, 45794, 46139, 46456, 46745, 47012, 47248, 47464, 47656, 47829, 47980, 48113, 48229,
        48329, 48416, 48490, 48551, 48601, 48643, 48676, 48703, 48723, 48736, 48745, 48748, 48747, 48741, 48728, 48714,
        48693, 48667, 48635, 48595, 48550, 48497, 48436, 48364, 48284, 48193, 48090, 47974, 47846, 47706, 47550, 47380,
        47192, 46991, 46774, 46540, 46289, 46023, 45740, 45441, 45125, 44794, 44446, 44084, 43708, 43316, 42915, 42499,
        42073, 41634, 41187, 40727, 40263, 39791, 39311, 38826, 38337, 37843, 37348, 36850, 36350, 35850, 35350, 34852,
        34356, 33862, 33369, 32882, 32401, 31923, 31451, 30983, 30524, 30072, 29626, 29187, 28759, 28338, 27928, 27527,
        27135, 26754, 26385, 26024, 25678, 25343, 25020, 24708, 24412, 24128, 23858, 23602, 23360, 23134, 22922, 22727,
        22547, 22383, 22235, 22105, 21991, 21894, 21816, 21755, 21711, 21687, 21680, 21693, 21724, 21775, 21845, 21934,
        22044, 22172, 22320, 22487, 22677, 22885, 23113, 23363, 23631, 23921, 24229, 24558, 24908, 25279, 25671, 26081,
        26514, 26965, 27437, 27932, 28443, 28979, 29533, 30108, 30703, 31318, 31954, 32607, 33281, 33975, 34687, 35416,
        36163, 36925, 37703, 38490, 39289, 40096, 40909, 41719, 42527, 43324, 44108, 44867, 45598, 46286, 46925, 47500,
        47996, 48401, 48694, 48858, 48869, 48707, 48340, 47746, 46886, 45734, 44239, 42380, 40091, 37352, 34077, 30264,
        25772, 21005, 16784, 13147, 10049, 7453, 5312, 3592, 2252, 1258, 572, 166, 4, 62, 308, 722,
        1277, 1954, 2735, 3599, 4533, 5522, 6558, 7622, 8712, 9817, 10931, 12049, 13166, 14275, 15381, 16475,
        17558, 18628, 19685, 20730, 21760, 22777, 23780, 24757, 25723, 26697, 27638, 28588, 29498, 30430, 31300, 32236,
    ];

    /* Adventure Kid Waveforms (AKWF) converted for use with Teensy Audio Library
*
*  Adventure Kid Waveforms(AKWF) Open waveforms library
*  https://www.adventurekid.se/akrt/waveforms/adventure-kid-waveforms/
*
*  This code is in the public domain, CC0 1.0 Universal (CC0 1.0)
*  https://creativecommons.org/publicdomain/zero/1.0/
*
*  Converted by Brad Roy, https://github.com/prosper00
*/

    /* AKWF_granular_0044 256 samples

      +-----------------------------------------------------------------------------------------------------------------+
      |                     **   **                                                                                     |
      |                    **     *             ***                                                                     |
      |                   *       *            **  ***                                                                  |
      |                  **       *           *      ***                                                                |
      |                  *        *          **        *                                                                |
      |    ***          *         *          *         *                                                                |
      | ***  *          *         *         **         *                                                                |
      |*     *         **         *         *          *        ********************************************************|
      |      *         *          *         *          *      **                                                        |
      |      **       *           *        *           *   ****                                                         |
      |       ****   **           *        *           *****                                                            |
      |          ****             *       **           **                                                               |
      |                           *       *                                                                             |
      |                           *      **                                                                             |
      |                           **    **                                                                              |
      +-----------------------------------------------------------------------------------------------------------------+


    */


    static granular_0044 = [
        32869, 33554, 33950, 34774, 35134, 36047, 36319, 37297, 37454, 38494, 38511, 39617, 39443, 40664, 40161, 41814,
        38882, 23368, 22518, 21974, 20997, 20545, 19523, 19169, 18210, 17982, 17163, 17128, 16552, 16803, 16594, 17281,
        17607, 18928, 20002, 22162, 24166, 27270, 30129, 33900, 37194, 41086, 44210, 47679, 50274, 53080, 55123, 57263,
        58843, 60380, 61646, 62635, 63750, 64193, 65294, 65000, 65535, 64171, 65114, 62655, 64487, 59956, 65114, 36210,
        212, 3832, 99, 1558, 1, 510, 0, 197, 120, 547, 1094, 1697, 2901, 3914, 5892, 7586,
        10533, 13157, 17216, 20988, 26107, 30361, 35515, 39386, 43777, 46670, 49891, 51621, 53703, 54463, 55644, 55730,
        56241, 55895, 55900, 55320, 54914, 54268, 53486, 52949, 51761, 51561, 49784, 50399, 47306, 51139, 28999, 14730,
        19959, 17550, 20023, 18982, 20690, 20318, 21655, 21737, 22859, 23286, 24286, 24994, 25914, 26840, 27701, 28756,
        29549, 30623, 31268, 32196, 32566, 33184, 33197, 33422, 33100, 32970, 32677, 32843, 32704, 32820, 32726, 32801,
        32745, 32785, 32759, 32771, 32771, 32760, 32779, 32753, 32784, 32751, 32787, 32749, 32786, 32751, 32785, 32753,
        32782, 32756, 32779, 32759, 32775, 32762, 32773, 32765, 32771, 32768, 32768, 32769, 32767, 32769, 32766, 32770,
        32766, 32769, 32767, 32770, 32767, 32769, 32767, 32770, 32768, 32768, 32768, 32768, 32768, 32768, 32768, 32768,
        32768, 32767, 32767, 32768, 32767, 32768, 32767, 32768, 32769, 32768, 32768, 32768, 32768, 32768, 32768, 32768,
        32767, 32768, 32768, 32768, 32769, 32768, 32768, 32768, 32767, 32768, 32768, 32769, 32768, 32768, 32767, 32769,
        32767, 32769, 32768, 32769, 32767, 32768, 32767, 32768, 32768, 32768, 32768, 32767, 32770, 32767, 32770, 32766,
        32771, 32765, 32772, 32762, 32775, 32757, 32786, 32653, 32303, 32073, 32011, 32104, 32434, 32756, 32768, 32767,
    ];


}
// js/audio/puredata.js
/*
    This file implements PureData DSP functions to operate on audio buffers.
*/

const PD_COSTABLESIZE = 2048;
const PD_UNITBIT32 = 1572864;  /* 3*2^19; bit 32 has place value 1 */
const PD_HIOFFSET = 1;
const PD_LOWOFFSET = 0;

var COSTABLENAME;

function generate_tables(){
    COSTABLENAME = new Float32Array(PD_COSTABLESIZE+1);
    for (let i = 0; i < PD_COSTABLESIZE; i++) {
        COSTABLENAME[i] = Math.cos( 2 * Math.PI * i / PD_COSTABLESIZE);
    }
    COSTABLENAME[0] = 1;
    COSTABLENAME[PD_COSTABLESIZE] = 1;
    COSTABLENAME[(PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(3*PD_COSTABLESIZE/4)|0] = 0;
    COSTABLENAME[(PD_COSTABLESIZE/2)|0] = -1;
}

function gt(signal_a,signal_b){
    var result = new Float32Array(signal_a.length);
    for (let i = 0; i < signal_a.length; i++) {
        result[i] = signal_a[i] < signal_b[i] ? 1 : 0;
    }
    return result;
}

generate_tables();
var puredata_stream_length = 0;
function pd_set_stream_length_seconds(seconds){
    puredata_stream_length = seconds * SAMPLE_RATE;
}

function pd_fn(fn){
    var result = new Float32Array(puredata_stream_length);
    for (let i = 0; i < result.length; i++) {
        result[i] = fn(i/SAMPLE_RATE);
    }
    return result;
}

// white noise signal (in the range from -1 to 1).
// https://pd.iem.sh/objects/noise~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.c#L372
function pd_noise(){
    var result = new Float32Array(puredata_stream_length);
    for (let i = 0; i < result.length; i++) {
        result[i] = Math.random() * 2 - 1;
    }
    return result;
}

function pd_clip(buffer, min_signal, max_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = Math.max(min_signal[i], Math.min(buffer[i], max_signal[i]));
    }
    return result;
}

// cosine wave oscillator
// https://pd.iem.sh/objects/osc~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.h#L73C1-L99C6
function pd_osc(freq_signal){
    /* original code:
    t_osc *x = (t_osc *)(w[1]);
    t_sample *in = (t_sample *)(w[2]);
    t_sample *out = (t_sample *)(w[3]);
    int n = (int)(w[4]);
    float *tab = COSTABLENAME, *addr;
    t_float f1, f2, frac;
    double dphase = x->x_phase + UNITBIT32;
    int normhipart;
    union tabfudge tf;
    float conv = x->x_conv;

    tf.tf_d = UNITBIT32;
    normhipart = tf.tf_i[HIOFFSET];
#if 0
    while (n--)
    {
        tf.tf_d = dphase;
        dphase += *in++ * conv;
        addr = tab + (tf.tf_i[HIOFFSET] & (COSTABLESIZE-1));
        tf.tf_i[HIOFFSET] = normhipart;
        frac = tf.tf_d - UNITBIT32;
        f1 = addr[0];
        f2 = addr[1];
        *out++ = f1 + frac * (f2 - f1);
    }
        */
    var result = new Float32Array(freq_signal.length);
    let dphase = PD_UNITBIT32;
    let conv = 2 * Math.PI / SAMPLE_RATE;

    // The bit manipulation in C is not directly translatable to JavaScript
    // Instead, we'll use a simpler approach that achieves the same result
    let phase = 0;

    for (let i = 0; i < freq_signal.length; i++) {
        // Update phase based on frequency
        phase += freq_signal[i] * conv;

        // Keep phase in [-π, π] for both positive and negative frequencies
        while (phase >= Math.PI) {
            phase -= 2 * Math.PI;
        }
        while (phase < -Math.PI) {
            phase += 2 * Math.PI;
        }

        // Get table index and fractional part
        let index = (((phase + Math.PI) / (2 * Math.PI)) * PD_COSTABLESIZE)|0;
        let idx1 = Math.floor(index) % PD_COSTABLESIZE;
        let idx2 = (idx1 + 1) % PD_COSTABLESIZE;
        let frac = index - idx1;

        // Linear interpolation between adjacent table values
        let f1 = COSTABLENAME[idx1];
        let f2 = COSTABLENAME[idx2];
        result[i] = f1 + frac * (f2 - f1);
    }

    return result;
}

function pd_mul(buffer, multiplier_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] * multiplier_signal[i];
    }
    return result;
}

function pd_div(buffer, divisor_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] / divisor_signal[i];
    }
    return result;
}

function pd_add(buffer, addend_signal){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = buffer[i] + addend_signal[i];
    }
    return result;
}

function pd_polyadd(...buffers){
    var result = new Float32Array(buffers[0].length);
    for (let i = 0; i < result.length; i++) {
        result[i] = buffers[0][i];
        for (let j = 1; j < buffers.length; j++) {
            result[i] += buffers[j][i];
        }
    }
    return result;
}

function pd_c(value){
    var result = new Float32Array(puredata_stream_length);
    result.fill(value);
    return result;
}

function pd_abs(buffer){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = Math.abs(buffer[i]);
    }
    return result;
}

function pd_sqrt(buffer){
    var result = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
        result[i] = Math.sqrt(buffer[i]);
    }
    return result;
}

function sigbp_qcos(f)
{
    if (f >= -(0.5*Math.PI) && f <= 0.5*Math.PI)
    {
        var g = f*f;
        return (((g*g*g * (-1.0/720.0) + g*g*(1.0/24.0)) - g*0.5) + 1);
    }
    else {
        return 0;
    }
}

/*
// ---------------- bp~ - 2-pole bandpass filter. -----------------

typedef struct bpctl
{
    t_sample c_x1;
    t_sample c_x2;
    t_sample c_coef1;
    t_sample c_coef2;
    t_sample c_gain;
} t_bpctl;

typedef struct sigbp
{
    t_object x_obj;
    t_float x_sr;
    t_float x_freq;
    t_float x_q;
    t_bpctl x_cspace;
    t_float x_f;
} t_sigbp;

t_class *sigbp_class;

static void sigbp_docoef(t_sigbp *x, t_floatarg f, t_floatarg q);

static void *sigbp_new(t_floatarg f, t_floatarg q)
{
    t_sigbp *x = (t_sigbp *)pd_new(sigbp_class);
    inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("float"), gensym("ft1"));
    inlet_new(&x->x_obj, &x->x_obj.ob_pd, gensym("float"), gensym("ft2"));
    outlet_new(&x->x_obj, &s_signal);
    x->x_sr = 44100;
    x->x_cspace.c_x1 = 0;
    x->x_cspace.c_x2 = 0;
    sigbp_docoef(x, f, q);
    x->x_f = 0;
    return (x);
}

static t_float sigbp_qcos(t_float f)
{
    if (f >= -(0.5f*3.14159f) && f <= 0.5f*3.14159f)
    {
        t_float g = f*f;
        return (((g*g*g * (-1.0f/720.0f) + g*g*(1.0f/24.0f)) - g*0.5) + 1);
    }
    else return (0);
}

static void sigbp_docoef(t_sigbp *x, t_floatarg f, t_floatarg q)
{
    t_float r, oneminusr, omega;
    if (f < 0.001) f = 10;
    if (q < 0) q = 0;
    x->x_freq = f;
    x->x_q = q;
    omega = f * (2.0f * 3.14159f) / x->x_sr;
    if (q < 0.001) oneminusr = 1.0f;
    else oneminusr = omega/q;
    if (oneminusr > 1.0f) oneminusr = 1.0f;
    r = 1.0f - oneminusr;
    x->x_cspace.c_coef1 = 2.0f * sigbp_qcos(omega) * r;
    x->x_cspace.c_coef2 = - r * r;
    x->x_cspace.c_gain = 2 * oneminusr * (oneminusr + r * omega);
}

static void sigbp_ft1(t_sigbp *x, t_floatarg f)
{
    sigbp_docoef(x, f, x->x_q);
}

static void sigbp_ft2(t_sigbp *x, t_floatarg q)
{
    sigbp_docoef(x, x->x_freq, q);
}

static void sigbp_clear(t_sigbp *x, t_floatarg q)
{
    x->x_cspace.c_x1 = x->x_cspace.c_x2 = 0;
}

static t_int *sigbp_perform(t_int *w)
{
    t_sample *in = (t_sample *)(w[1]);
    t_sample *out = (t_sample *)(w[2]);
    t_bpctl *c = (t_bpctl *)(w[3]);
    int n = (int)w[4];
    int i;
    t_sample last = c->c_x1;
    t_sample prev = c->c_x2;
    t_sample coef1 = c->c_coef1;
    t_sample coef2 = c->c_coef2;
    t_sample gain = c->c_gain;
    for (i = 0; i < n; i++)
    {
        t_sample output =  *in++ + coef1 * last + coef2 * prev;
        *out++ = gain * output;
        prev = last;
        last = output;
    }
    if (PD_BIGORSMALL(last))
        last = 0;
    if (PD_BIGORSMALL(prev))
        prev = 0;
    c->c_x1 = last;
    c->c_x2 = prev;
    return (w+5);
}

*/

// 2-pole bandpass filter
// https://pd.iem.sh/objects/bp~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_filter.c#L325
function pd_bp(buffer, center_freq_signal, q_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let last = buffer[0];
    let prev = buffer[0];

    for (let i = 0; i < buffer.length; i++) {
        let f = center_freq_signal[i];
        let q = q_signal[i];
        if (f < 0.001) f = 10;
        if (q < 0) q = 0;

        let omega = f * (2.0 * Math.PI) / SAMPLE_RATE;
        let oneminusr;

        if (q < 0.001) {
            oneminusr = 1.0;
        } else {
            oneminusr = omega/q;
        }
        if (oneminusr > 1.0) oneminusr = 1.0;

        let r = 1.0 - oneminusr;
        let coef1 = 2.0 * sigbp_qcos(omega) * r;
        let coef2 = -r * r;
        let gain = 2 * oneminusr * (oneminusr + r * omega);

        let input = buffer[i];
        let output = input + coef1 * last + coef2 * prev;
        output_buffer[i] = gain * output;
        prev = last;
        last = output;
    }
    return output_buffer;
}


// lop one-pole low pass filter.
// https://pd.iem.sh/objects/lop~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_filter.c#L139
function pd_lop(buffer, filter_coeff_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let last =  buffer[0];

    for (let i = 0; i < buffer.length; i++) {
        let coef = filter_coeff_signal[i]*CONVERSION_FACTOR;
        if (coef > 1){
            coef = 1;
        }
        if (coef < 0){
            coef = 0;
        }
        last = coef * buffer[i] + (1-coef) * last;
        output_buffer[i] = last;
    }

    return output_buffer;
}

// hip one-pole high pass filter.
// https://pd.iem.sh/objects/hip~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_filter.c#L9
function pd_hip(buffer, filter_coeff_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let last =  buffer[0];

    for (let i = 0; i < buffer.length; i++) {
        let f = filter_coeff_signal[i];
        let coef = 1 - f*CONVERSION_FACTOR;
        if (coef< 0){
            coef = 0;
        }
        else if (coef > 1){
            coef = 1;
        }

        if (coef < 1){
            const normal = 0.5*(1+coef);
            const cur = buffer[i] + coef*last;
            output_buffer[i] = normal*(cur-last);
            last = cur;
        }
        else {
            output_buffer[i] = buffer[i];
        }
    }

    return output_buffer;
}


/* voltage-controlled band/low-pass filter
    1st
    signal - audio signal to be filtered.
    2nd
    signal - resonant frequency in Hz.
    3rd
    float - set Q.
*/
// https://pd.iem.sh/objects/vcf~/
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.c#L289
// https://github.com/pure-data/pure-data/blob/12de13067aee29e332a34eb3539fa3cb967b63a1/src/d_osc.h#L131
// absolute black magic.  Don't understand it - did my best, then let cursor fix it.
function pd_vcf(buffer, res_freq_signal, q_signal) {
    let output_buffer = new Float32Array(buffer.length);
    let re = 0;
    let im = 0;

    // Create a proper tabfudge-like structure to match the original C code
    let tf = {
        d: 0,
        i: new Uint32Array(2)
    };

    // Get the normhipart constant similar to the C code
    tf.d = PD_UNITBIT32;
    const normhipart = tf.i[PD_HIOFFSET];

    for (let i = 0; i < buffer.length; i++) {
        let q = q_signal[i];
        let qinv = q > 0 ? (1/q) : 0;
        let ampcorrect = 2 - 2/(q+2);
        let coefr = 0;
        let coefi = 0;
        let tab = COSTABLENAME;

        // Get the frequency coefficient - use the right conversion factor
        let cf = res_freq_signal[i] * CONVERSION_FACTOR;
        if (cf < 0) cf = 0;

        // Use the same conversion as in the original C code
        let cfindx = cf * (PD_COSTABLESIZE/6.28318);

        // Calculate resonance factor
        let r = (qinv > 0) ? (1 - cf * qinv) : 0;
        if (r < 0) r = 0;
        let oneminusr = 1 - r;

        // Bit-twiddling to get the table index and fraction - similar to original code
        let dphase = cfindx + PD_UNITBIT32;
        tf.d = dphase;
        let tabindex = tf.i[PD_HIOFFSET] & (PD_COSTABLESIZE-1);

        tf.i[PD_HIOFFSET] = normhipart;
        let frac = tf.d - PD_UNITBIT32;

        // Get the real coefficient using interpolation
        let f1 = tab[tabindex];
        let f2 = tab[tabindex+1];
        coefr = r * (f1 + frac * (f2 - f1));

        // Get the imaginary coefficient using interpolation
        tabindex = ((tabindex - (PD_COSTABLESIZE/4)) & (PD_COSTABLESIZE-1));
        f1 = tab[tabindex];
        f2 = tab[tabindex+1];
        coefi = r * (f1 + frac * (f2 - f1));

        // Apply the filter
        let inputSample = buffer[i];
        let re2 = re;
        re = ampcorrect * oneminusr * inputSample + coefr * re2 - coefi * im;
        im = coefi * re2 + coefr * im;

        // Handle numerical instability
        if (Math.abs(re) < 1e-10) re = 0;
        if (Math.abs(im) < 1e-10) im = 0;

        output_buffer[i] = re;
    }

    return output_buffer;
}

// js/audio/Bfxr_DSP.js
/**
 *
 * this uses ported/modified code from Thomas Vian's SfxrSynth:
	 * SfxrSynth
	 *
	 * Copyright 2010 Thomas Vian
	 *
	 * Licensed under the Apache License, Version 2.0 (the "License");
	 * you may not use this file except in compliance with the License.
	 * You may obtain a copy of the License at
	 *
	 * 	http://www.apache.org/licenses/LICENSE-2.0
	 *
	 * Unless required by applicable law or agreed to in writing, software
	 * distributed under the License is distributed on an "AS IS" BASIS,
	 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	 * See the License for the specific language governing permissions and
	 * limitations under the License.
	 *
	 * @author Thomas Vian
	 */

class Bfxr_DSP {
    static version = "1.0.4"

    static MIN_LENGTH = 0.18;
    static LoResNoisePeriod = 8;
    static sampleRate = 44100;
    static bitDepth = 16;

    constructor(params,param_info) {

        this.params = params;
        this.param_info = param_info;

        this.reset(true);
    }

    /*
     * Resets the runing variables from the params
     * Used once at the start (total reset) and for the repeat effect (partial reset)
     * */
    reset(total_reset = true){
        var params=this.params;


        this.frequency_period_samples = 100.0 / (params.frequency_start * params.frequency_start + 0.001);
        var minimum_frequency = Math.pow(params.min_frequency_relative_to_starting_frequency,0.4)*params.frequency_start;
        this.frequency_maxPeriod_samples = 100.0 / (minimum_frequency * minimum_frequency + 0.001);

        this.pitch_jump_reached = false;
        this.pitch_jump_2_reached = false;

        if (total_reset){

            this.masterVolume = params.masterVolume * params.masterVolume;

            this.waveType = (params.waveType)|0;

            if (params.sustainTime < 0.01) {
                params.sustainTime = 0.01;
            }

            this.clampTotalLength(params);

            this.sustainPunch = params.sustainPunch;

            this.phase = 0;

            this.minFreqency = params.min_frequency_relative_to_starting_frequency;
            this.muted = false;
            this.overtones = params.overtones * 10;
            this.overtoneFalloff = params.overtoneFalloff;

            this.compression_factor = 1 / (1 + 4 * params.compressionAmount);

            this.filters = params.lpFilterCutoff != 1.0 || params.hpFilterCutoff != 0.0;



            this.vibratoPhase = 0.0;
            this.vibratoSpeed = params.vibratoSpeed * params.vibratoSpeed * 0.01;
            this.vibratoAmplitude = params.vibratoDepth * 0.5;

            this.envelopeVolume = 0.0;
            this.envelopeStage = 0;
            this.envelopeTime = 0;
            this.envelopeLength0 = params.attackTime * params.attackTime * 100000.0;
            this.envelopeLength1 = params.sustainTime * params.sustainTime * 100000.0;
            this.envelopeLength2 = params.decayTime * params.decayTime * 100000.0 + 10;
            this.attack_length_samples = this.envelopeLength0;
            this.envelope_full_length_samples = this.envelopeLength0 + this.envelopeLength1 + this.envelopeLength2;


            this.bitcrush_freq_sweep = -params.bitCrushSweep / this.envelope_full_length_samples;
            this.bitcrush_phase = 0;
            this.bitcrush_last = 0;


            this.envelopeOverLength0 = 1.0 / this.envelopeLength0;
            this.envelopeOverLength1 = 1.0 / this.envelopeLength1;
            this.envelopeOverLength2 = 1.0 / this.envelopeLength2;

            this.flanger = params.flangerOffset != 0.0 || params.flangerSweep != 0.0;

            this.flangerDeltaOffset = params.flangerSweep * params.flangerSweep * params.flangerSweep * 0.2;
            this.flangerPos = 0;

            if (!this.flangerBuffer) {
                this.flangerBuffer = new Float32Array(1024);
            }
            if (!this.noiseBuffer) {
                this.noiseBuffer = new Float32Array(32);
            }
            if (!this.pinkNoiseBuffer) {
                this.pinkNoiseBuffer = new Float32Array(32);
            }
            if (!this.loResNoiseBuffer) {
                this.loResNoiseBuffer = new Float32Array(32);
            }
            this.oneBitNoiseState = 1 << 14;
            this.oneBitNoise = 0;
            this.buzzState = 1 << 14;
            this.buzz = 0;

            for (var i = 0; i < 1024; i++) {
                this.flangerBuffer[i] = 0.0;
            }
            for (i = 0; i < 32; i++) {
                this.noiseBuffer[i] = Math.random() * 2.0 - 1.0;
            }
            for (i = 0; i < 32; i++) {
                this.loResNoiseBuffer[i] = ((i % Bfxr_DSP.LoResNoisePeriod) == 0) ? Math.random() * 2.0 - 1.0 : this.loResNoiseBuffer[i - 1];
            }

            this.repeat_timestamp_samples = 0;

            //if
            // when params.pitch_jump_repeat_speed is zero, it should not repeat (i.e. pitch_jump_repeat_length_samples should be the same as the envelope length)
            // when params.pitch_jump_repeat_speed is 1, it should repeat 10 times a second (i.e. sampleRate/50)
            this.pitch_jump_repeat_length_samples = lerp(this.envelope_full_length_samples, Bfxr_DSP.sampleRate/50, params.pitch_jump_repeat_speed)+32;//adding 32 for safety

            // PITCH JUMP START


            var pitch_jump_window_size_samples = this.envelope_full_length_samples;
            if (this.pitch_jump_repeat_length_samples > 0) {
                pitch_jump_window_size_samples = this.pitch_jump_repeat_length_samples;
            }

            if (params.pitch_jump_amount > 0.0) {
                this.pitch_jump_amount = 1.0 - params.pitch_jump_amount * params.pitch_jump_amount * 0.9;
            }
            else {
                this.pitch_jump_amount = 1.0 + params.pitch_jump_amount * params.pitch_jump_amount * 10.0;
            }
            if (params.pitch_jump_2_amount > 0.0) {
                this.pitch_jump_2_amount = 1.0 - params.pitch_jump_2_amount * params.pitch_jump_2_amount * 0.9;
            }
            else {
                this.pitch_jump_2_amount = 1.0 + params.pitch_jump_2_amount * params.pitch_jump_2_amount * 10.0;
            }

            this.pitch_jump_current_timestamp_samples = 0;

            if (params.pitch_jump_onset_percent == 1.0) {
                this.pitch_jump_timestamp_sample = 0;
            }
            else {
                this.pitch_jump_timestamp_sample = params.pitch_jump_onset_percent * pitch_jump_window_size_samples + 32;
            }
            if (params.pitch_jump_onset2_percent == 1.0) {
                this.pitch_jump_2_timestamp_sample = 0;
            }
            else {
                this.pitch_jump_2_timestamp_sample = params.pitch_jump_onset2_percent * pitch_jump_window_size_samples + 32;
            }

            //scale by repeat_length_samples vs envelope_full_length_samples
            //need to scale by repeat_length_samples/envelope_full_length_samples
            // var pitch_jump_time_scale_factor = this.pitch_jump_repeat_length_samples / this.envelope_full_length_samples;
            // this.pitch_jump_timestamp_sample *= pitch_jump_time_scale_factor;
            // this.pitch_jump_2_timestamp_sample *= pitch_jump_time_scale_factor;

            //PITCH JUMP END

            if (this.waveType === 9) { //Bitnoise
                var sf = params.frequency_start;
                var mf = params.min_frequency_relative_to_starting_frequency;

                var startFrequency_min = this.param_info.param_min("frequency_start");
                var startFrequency_max = this.param_info.param_max("frequency_start");
                var startFrequency_mid = (startFrequency_max + startFrequency_min) / 2;

                var minFrequency_min = this.param_info.param_min("min_frequency_relative_to_starting_frequency");
                var minFrequency_max = this.param_info.param_max("min_frequency_relative_to_starting_frequency");
                var minFrequency_mid = (minFrequency_max + minFrequency_min) / 2;

                var delta_start = (sf - startFrequency_min) / (startFrequency_max - startFrequency_min)
                var delta_min = (mf - minFrequency_min) / (minFrequency_max - minFrequency_min)

                sf = startFrequency_mid + delta_start;
                mf = minFrequency_mid + delta_min;

                this.frequency_period_samples = 100.0 / (sf * sf + 0.001);
                this.frequency_maxPeriod_samples = 100.0 / (mf * mf + 0.001);
            }
        }

        // START sweep paramets designed to be reset with repeat speed
        this.slide = 1.0 - params.frequency_slide * params.frequency_slide * params.frequency_slide * 0.01;
        this.frequency_acceleration = -params.frequency_acceleration * params.frequency_acceleration * params.frequency_acceleration * 0.000001;

        this.flangerOffset = params.flangerOffset * params.flangerOffset * 1020.0;
        if (params.flangerOffset < 0.0) {
            this.flangerOffset = -this.flangerOffset;
        }

        this.bitcrush_freq = 1 - Math.pow(params.bitCrush, 1.0 / 3.0);


        if ((params.waveType)|0 == 0) {
            this.squareDuty = 0.5 - params.squareDuty * 0.5;
            this.dutySweep = -params.dutySweep * 0.00005;
        }

        this.lpFilterCutoff = params.lpFilterCutoff * params.lpFilterCutoff * params.lpFilterCutoff * 0.1;
        this.lpFilterDeltaCutoff = 1.0 + params.lpFilterCutoffSweep * 0.0001;
        this.lpFilterDamping = 5.0 / (1.0 + params.lpFilterResonance * params.lpFilterResonance * 20.0) * (0.01 + this.lpFilterCutoff);
        if (this.lpFilterDamping > 0.8) this.lpFilterDamping = 0.8;
        this.lpFilterDamping = 1.0 - this.lpFilterDamping;
        this.lpFilterOn = params.lpFilterCutoff != 1.0;

        this.lpFilterPos = 0.0;
        this.lpFilterDeltaPos = 0.0;
        this.hpFilterPos = 0.0;
        this.hpFilterCutoff = params.hpFilterCutoff * params.hpFilterCutoff * 0.1;
        this.hpFilterDeltaCutoff = 1.0 + params.hpFilterCutoffSweep * 0.0003;

        // END sweep paramets designed to be reset with repeat speed


        // when params.pitch_jump_repeat_speed, it should not repeat (i.e. be the same as the envelope length)
        // when params.pitch_jump_repeat_speed is 1, it should repeat 10 times a second (i.e. sampleRate/10)
        this.param_reset_period_samples = lerp(this.envelope_full_length_samples, Bfxr_DSP.sampleRate/10, params.repeatSpeed);
        this.param_reset_current_timestamp_samples = 0;



    }

    clampTotalLength(p)
    {
        var totalTime = p.attackTime + p.sustainTime + p.decayTime;
        if (totalTime < Bfxr_DSP.MIN_LENGTH )
        {
            var multiplier = Bfxr_DSP.MIN_LENGTH / totalTime;
            p.attackTime = p.attackTime * multiplier;
            p.sustainTime = p.sustainTime * multiplier;
            p.decayTime = p.decayTime * multiplier;
        }
    }

    generate_sound() {
        var buffer = new Float32Array(this.envelope_full_length_samples);

        this.sampleCount = 0;
        var bufferSample = 0.0;

        var length = this.envelope_full_length_samples;
        var finished = false;
        var last_nonzero_sample_index = -1;
        for(var i = 0; i < length; i++)
        {
            if (finished)
            {
                return true;
            }

            // Repeats every this.pitch_jump_repeat_length_samples times, partially resetting the sound parameters
            if(this.param_reset_period_samples != 0)
            {
                this.param_reset_current_timestamp_samples++;
                if(this.param_reset_current_timestamp_samples >= this.param_reset_period_samples)
                {
                    this.param_reset_current_timestamp_samples = 0;
                    this.reset(false);
                }
            }

            this.pitch_jump_current_timestamp_samples++;
            if (this.pitch_jump_current_timestamp_samples>=this.pitch_jump_repeat_length_samples)
            {
                this.pitch_jump_current_timestamp_samples=0;
                if (this.pitch_jump_reached)
                {
                    this.frequency_period_samples /= this.pitch_jump_amount;
                    this.pitch_jump_reached=false;
                }
                if (this.pitch_jump_2_reached)
                {
                    this.frequency_period_samples /= this.pitch_jump_2_amount;
                    this.pitch_jump_2_reached=false;
                }
            }

            // If this.pitch_jump_timestamp_sample is reached, shifts the pitch
            if(!this.pitch_jump_reached)
            {
                if(this.pitch_jump_current_timestamp_samples >= this.pitch_jump_timestamp_sample)
                {
                    this.pitch_jump_reached = true;
                    this.frequency_period_samples *= this.pitch_jump_amount;
                }
            }

            // If this.pitch_jump_timestamp_sample is reached, shifts the pitch
            if(!this.pitch_jump_2_reached)
            {
                if(this.pitch_jump_current_timestamp_samples >= this.pitch_jump_2_timestamp_sample)
                {
                    this.frequency_period_samples *= this.pitch_jump_2_amount;
                    this.pitch_jump_2_reached=true;
                }
            }

            // Acccelerate and apply slide
            this.slide += this.frequency_acceleration;
            this.frequency_period_samples *= this.slide;

            // Checks for frequency getting too low, and stops the sound if a min_frequency_relative_to_starting_frequency was set
            if(this.frequency_period_samples > this.frequency_maxPeriod_samples)
            {
                this.frequency_period_samples = this.frequency_maxPeriod_samples;
                if(this.minFreqency > 0.0) {
                        this.muted = true;
                }
            }

            this.periodTemp = this.frequency_period_samples;

            // Applies the vibrato effect
            if(this.vibratoAmplitude > 0.0)
            {
                this.vibratoPhase += this.vibratoSpeed;
                this.periodTemp = this.frequency_period_samples * (1.0 + Math.sin(this.vibratoPhase) * this.vibratoAmplitude);
            }

            this.periodTemp = (this.periodTemp)|0;
            if(this.periodTemp < 8) this.periodTemp = 8;

            // Sweeps the square duty
            if (this.waveType === 0)
            {
                this.squareDuty += this.dutySweep;
                if(this.squareDuty < 0.0) this.squareDuty = 0.001;
                else if (this.squareDuty > 0.5) this.squareDuty = 0.5;
            }

            // Moves through the different stages of the volume envelope
            if(++this.envelopeTime > this.attack_length_samples)
            {
                this.envelopeTime = 0;

                switch(++this.envelopeStage)
                {
                    case 1: this.attack_length_samples = this.envelopeLength1; break;
                    case 2: this.attack_length_samples = this.envelopeLength2; break;
                }
            }

            // Sets the volume based on the position in the envelope
            switch(this.envelopeStage)
            {
                case 0:
                    this.envelopeVolume = this.envelopeTime * this.envelopeOverLength0;
                    break;
                case 1:
                    this.envelopeVolume = 1.0 + (1.0 - this.envelopeTime * this.envelopeOverLength1) * 2.0 * this.sustainPunch;
                        break;
                case 2:
                    this.envelopeVolume = 1.0 - this.envelopeTime * this.envelopeOverLength2;
                    break;
                case 3:
                    this.envelopeVolume = 0.0; finished = true;
                    break;
            }

            // Moves the flanger offset
            if (this.flanger)
            {
                this.flangerOffset += this.flangerDeltaOffset;
                this.flangerInt = (this.flangerOffset)|0;
                        if(this.flangerInt < 0) 	this.flangerInt = -this.flangerInt;
                else if (this.flangerInt > 1023) this.flangerInt = 1023;
            }

            // Moves the high-pass filter cutoff
            if(this.filters && this.hpFilterDeltaCutoff != 0.0)
            {
                this.hpFilterCutoff *= this.hpFilterDeltaCutoff;
                        if(this.hpFilterCutoff < 0.00001) 	this.hpFilterCutoff = 0.00001;
                else if(this.hpFilterCutoff > 0.1) 		this.hpFilterCutoff = 0.1;
            }

            this.superSample = 0.0;
            for(var j = 0; j < 8; j++)
            {
                // Cycles through the period
                this.phase++;
                if(this.phase >= this.periodTemp)
                {
                    this.phase = this.phase - this.periodTemp;

                    // Generates new random noise for this period
                    switch(this.waveType)
                    {
                        case 3:  // WHITE NOISE
                            for(var n = 0; n < 32; n++) this.noiseBuffer[n] = Math.random() * 2.0 - 1.0;
                            break;
                        case 6: // TAN
                            for(n = 0; n < 32; n++) this.loResNoiseBuffer[n] = ((n%Bfxr_DSP.LoResNoisePeriod)==0) ? Math.random()*2.0-1.0 : this.loResNoiseBuffer[n-1];
                            break;
                        case 9: // Bitnoise
                        // Based on SN76489 periodic "white" noise
                        // http://www.smspower.org/Development/SN76489?sid=ae16503f2fb18070f3f40f2af56807f1#NoiseChannel
                        // This one matches the behaviour of the SN76489 in the BBC Micro.
                        var feedBit = (this.oneBitNoiseState >> 1 & 1) ^ (this.oneBitNoiseState & 1);
                        this.oneBitNoiseState = this.oneBitNoiseState >> 1 | (feedBit << 14);
                        this.oneBitNoise = (~this.oneBitNoiseState & 1) - 0.5;
                        break;
                        // case 11: // BUZZ
                        //     // Based on SN76489 periodic "white" noise
                        //     // http://www.smspower.org/Development/SN76489?sid=ae16503f2fb18070f3f40f2af56807f1#NoiseChannel
                        //     // This one doesn't match the behaviour of anything real, but it made a nice sound, so I kept it.
                        // var fb = (this.buzzState >> 3 & 1) ^ (this.buzzState & 1);
                        // this.buzzState = this.buzzState >> 1 | (fb << 14);
                        // this.buzz = (~this.buzzState & 1) - 0.5;
                        // break;
                    }
                }

                this.sample=0;
                var overtonestrength=1;
                for (var k=0;k<=this.overtones;k++)
                {
                    var tempphase = (this.phase*(k+1))%this.periodTemp;
                    // Gets the sample from the oscillator
                    var wtype = this.waveType;

                    switch(wtype)
                    {
                        case 0: // Square wave
                        {
                            this.sample += overtonestrength*(((tempphase / this.periodTemp) < this.squareDuty) ? 0.5 : -0.5);
                            break;
                        }
                        case 1: // Saw wave
                        {
                            this.sample += overtonestrength*(1.0 - (tempphase / this.periodTemp) * 2.0);
                            break;
                        }
                        case 2: // Sine wave (fast and accurate approx)
                        {
                                this.pos = tempphase / this.periodTemp;
                                this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            var tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            this.sample += overtonestrength*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);
                            break;
                        }
                        case 3: // White Noise
                        {
                            this.sample += overtonestrength*(this.noiseBuffer[((tempphase * 32 / (this.periodTemp|0))|0)%32]);
                            break;
                        }
                        case 4: // Triangle Wave
                        {
                            this.sample += overtonestrength*(Math.abs(1-(tempphase / this.periodTemp)*2)-1);
                            break;
                        }
                        case 5: //Organ
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.granular_0044[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        }
                        case 6: // tan
                        {
                            //detuned
                            this.sample += Math.tan(Math.PI*tempphase/this.periodTemp)*overtonestrength;
                            break;
                        }
                        case 7: // Whistle
                        {
                            // Sin wave code
                            this.pos = tempphase / this.periodTemp;
                            this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            var value = 0.75*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);
                            //then whistle (essentially an overtone with frequencyx20 and amplitude0.25

                            this.pos = ((tempphase*20) % this.periodTemp) / this.periodTemp;
                            this.pos = this.pos > 0.5 ? (this.pos - 1.0) * 6.28318531 : this.pos * 6.28318531;
                            tempsample = this.pos < 0 ? 1.27323954 * this.pos + .405284735 * this.pos * this.pos : 1.27323954 * this.pos - 0.405284735 * this.pos * this.pos;
                            value += 0.25*(tempsample < 0 ? .225 * (tempsample *-tempsample - tempsample) + tempsample : .225 * (tempsample * tempsample - tempsample) + tempsample);

                            this.sample += overtonestrength*value;//main wave

                            break;
                        }
                        case 8: // Breaker
                        {
                            var amp = tempphase/this.periodTemp;
                            this.sample += overtonestrength*(Math.abs(1-amp*amp*2)-1);
                            break;
                        }
                        case 9: // Bitnoise (1-bit periodic "white" noise)
                        {
                            this.sample += overtonestrength*this.oneBitNoise;
                            break;
                        }
                        case 10: //FM Synth
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.fmsynth_0012[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        }
                        case 11: //Voice - wave sampled from AKWF_hvoice_0012
                        {
                            var sample_index = ((tempphase * 256 / (this.periodTemp|0))|0)%256;
                            var wave_sample = AKWF.hvoice_0012[sample_index]/32768-1;
                            this.sample += overtonestrength*wave_sample;
                            break;
                        }
                    }
                    overtonestrength*=(1-this.overtoneFalloff);

                }

                // Applies the low and high pass filters
                if (this.filters)
                {
                    this.lpFilterOldPos = this.lpFilterPos;
                    this.lpFilterCutoff *= this.lpFilterDeltaCutoff;
                            if(this.lpFilterCutoff < 0.0) this.lpFilterCutoff = 0.0;
                    else if(this.lpFilterCutoff > 0.1) this.lpFilterCutoff = 0.1;

                    if(this.lpFilterOn)
                    {
                        this.lpFilterDeltaPos += (this.sample - this.lpFilterPos) * this.lpFilterCutoff;
                        this.lpFilterDeltaPos *= this.lpFilterDamping;
                    }
                    else
                    {
                        this.lpFilterPos = this.sample;
                        this.lpFilterDeltaPos = 0.0;
                    }

                    this.lpFilterPos += this.lpFilterDeltaPos;

                    this.hpFilterPos += this.lpFilterPos - this.lpFilterOldPos;
                    this.hpFilterPos *= 1.0 - this.hpFilterCutoff;
                    this.sample = this.hpFilterPos;
                }

                // Applies the flanger effect
                if (this.flanger)
                {
                    this.flangerBuffer[this.flangerPos&1023] = this.sample;
                    this.sample += this.flangerBuffer[(this.flangerPos - this.flangerInt + 1024) & 1023];
                    this.flangerPos = (this.flangerPos + 1) & 1023;
                }

                this.superSample += this.sample;
            }

            // Clipping if too loud
            if(this.superSample > 8.0) 	this.superSample = 8.0;
            else if(this.superSample < -8.0) 	this.superSample = -8.0;



            //BIT CRUSH
            this.bitcrush_phase+=this.bitcrush_freq;
            if (this.bitcrush_phase>1)
            {
                this.bitcrush_phase=0;
                this.bitcrush_last=this.superSample;
            }
            var multiplier = lerp(1,50*this.bitcrush_freq,Math.sqrt(this.bitcrush_freq));
            this.bitcrush_freq = Math.max(Math.min(this.bitcrush_freq+multiplier*this.bitcrush_freq_sweep,1),0.00001);
            this.superSample=this.bitcrush_last;

            // Averages out the super samples and applies volumes
            this.superSample = this.masterVolume * this.envelopeVolume * this.superSample * 0.125;

            //compressor

            if (this.superSample>0)
            {
                this.superSample = Math.pow(this.superSample,this.compression_factor);
            }
            else
            {
                this.superSample = -Math.pow(-this.superSample,this.compression_factor);
            }

            if (this.muted)
            {
                //early out - resize buffer to current length, and return
                buffer = buffer.slice(0,i);
                break;
            }

            //approimxate zero (say ~ e-19)
            if (Math.abs(this.superSample)>0.2e-2){
                last_nonzero_sample_index = i;
            }
            buffer[i] = Math.clamp(this.superSample, -1, 1);
        }

        if (last_nonzero_sample_index<buffer.length-1){
            //min value of 10
            last_nonzero_sample_index = Math.max(last_nonzero_sample_index,10);
            buffer = buffer.slice(0,last_nonzero_sample_index+1);
        }
        this.buffer = buffer;
    }
}
// js/audio/Footsteppr_DSP.js
// Footstep synthesis from the existing PureData terrain patches, without playback.
class Footsteppr_DSP {
    static terrains = ['snow', 'grass', 'dirt', 'gravel', 'wood'];

    static render(params) {
        const length = 0.1 + 0.7 * (1 - params.swiftness);
        pd_set_stream_length_seconds(length);
        const envelope = resize_fn(add_fns(
            resize_fn(step(params.heel), 0, 1, 0, 0.3333),
            resize_fn(step(params.roll), 0, 1, 0.125, 0.875),
            resize_fn(step(params.ball), 0, 1, 0.6667, 1)
        ), 0, 1, 0, length);
        const terrain = this.terrains[params.terrain] || this.terrains[0];
        let signal = puredata_functions[terrain](pd_fn(envelope));
        signal = pd_mul(signal, pd_c(params.masterVolume));
        signal = pd_clip(signal, pd_c(-1), pd_c(1));
        return pd_mul(signal, pd_c(4));
    }
}

// js/audio/BfxrWaveforms.js
// Bfxr's oscillator palette for continuous-pitch engines. IDs match Bfxr;
// each renderer owns its noise state, so saved sounds replay deterministically.
class BfxrWaveforms {
    static choices = [
        ['Triangle','A soft triangular wave.',4],['Sin','A pure sine wave.',2],
        ['Square','A hollow pulse.',0],['Saw','A bright sawtooth.',1],
        ['Breaker','A curved, broken tooth.',8],['Tan','A sharply distorted tangent.',6],
        ['Whistle','A sine with a high overtone.',7],['White','Broadband noise.',3],
        ['Voice','Bfxr’s sampled vocal wave.',11],['Bitnoise','Periodic one-bit noise.',9],
        ['Rasp','Bfxr’s granular wavetable.',5],['FMSyn','Bfxr’s FM wavetable.',10]
    ];
    static blep(phase,step) {
        if(phase<step){const t=phase/step;return t+t-t*t-1;}
        if(phase>1-step){const t=(phase-1)/step;return t*t+t+t+1;}
        return 0;
    }
    static create(type,seed=0.5) {
        let state=(Math.round(seed*0xffffffff)|0)||1;
        const random=()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return (state>>>0)/2147483648-1;};
        let previous=1,cell=-1,white=0,bits=((state^0x4a35)&0x7fff)||1,bit=0.5;
        const table=type===5?AKWF.granular_0044:type===10?AKWF.fmsynth_0012:type===11?AKWF.hvoice_0012:null;
        return (phase,step)=>{
            if(phase<previous){cell=-1;const feed=(bits>>1&1)^(bits&1);bits=(bits>>1)|(feed<<14);bit=(~bits&1)-0.5;}
            previous=phase;
            if(table){const pos=phase*256,i=Math.floor(pos);return (table[i]+(table[(i+1)%256]-table[i])*(pos-i))/32768-1;}
            switch(type){
                case 0:return (phase<0.5?1:-1)+this.blep(phase,step)-this.blep((phase+0.5)%1,step);
                case 1:return 2*phase-1-this.blep(phase,step);
                case 3: {const next=Math.floor(phase*32);if(next!==cell){cell=next;white=random();}return white;}
                case 4:return 1-4*Math.abs(phase-0.5);
                case 6:return Math.max(-3,Math.min(3,Math.tan(Math.PI*phase)))/3;
                case 7:return .75*Math.sin(phase*2*Math.PI)+(step*20<.5?.25*Math.sin(phase*40*Math.PI):0);
                case 8:return 2*(Math.abs(1-2*phase*phase)-.609475708);
                case 9:return bit;
                default:return Math.sin(phase*2*Math.PI);
            }
        };
    }
}

// js/audio/Transfxr_DSP.js
// A continuous voice: curves move its controls between two states over time.
// No browser dependencies; output is mono PCM at the application's sample rate.
class Transfxr_DSP {
    static sampleRate = 44100;
    static curves = [
        ['Linear', t => t],
        ['Ease In', t => t * t],
        ['Ease Out', t => 1 - (1 - t) * (1 - t)],
        ['Smooth', t => t * t * (3 - 2 * t)],
        ['Triangle', t => 1 - Math.abs(2 * t - 1)],
        ['Pulse', t => (1 - Math.cos(2 * Math.PI * t)) / 2],
        ['Bounce', t => {
            // Ease-out bounce, bounded and ending exactly at the second state.
            if (t < 1 / 2.75) return 7.5625 * t * t;
            if (t < 2 / 2.75) { t -= 1.5 / 2.75; return 7.5625 * t * t + 0.75; }
            if (t < 2.5 / 2.75) { t -= 2.25 / 2.75; return 7.5625 * t * t + 0.9375; }
            t -= 2.625 / 2.75; return 7.5625 * t * t + 0.984375;
        }],
        ['Steps', t => Math.min(1, Math.floor(t * 5) / 4)]
    ];

    static frequency(value) { return 40 * Math.pow(2, value * 7); }
    static cutoff(value) { return 100 * Math.pow(160, value); }

    static transition(value) {
        const curve = (this.curves.find(c => c[0] === value.curve) || this.curves[0])[1];
        return t => value.start + (value.end - value.start) * curve(t);
    }

    // Polynomial correction removes the discontinuity at a saw/pulse edge.
    static polyBLEP(phase, step) {
        if (phase < step) { const t = phase / step; return t + t - t * t - 1; }
        if (phase > 1 - step) { const t = (phase - 1) / step; return t * t + t + t + 1; }
        return 0;
    }

    static render(p) {
        const rate = this.sampleRate;
        const count = Math.max(2, Math.round(p.duration * rate));
        const delay = Math.round(Math.min(0.24, Math.max(0.075, p.duration * 0.23)) * rate);
        const feedback = p.echo * 0.65;
        const repeats = feedback > 0 ? Math.ceil(Math.log(0.0001) / Math.log(feedback)) : 0;
        const tail = repeats * delay;
        const output = new Float32Array(count + tail);
        const controls = ['pitch', 'tone', 'vibrato', 'level'];
        const envelopes = controls.map(name => this.transition(p[name]));
        const values = controls.map(name => p[name].start);
        const attack = Math.max(0.003, p.attack) * rate;
        const release = Math.max(0.006, p.release) * rate;
        const damping = 1 / (0.707 + p.resonance * 5);
        const waveform = BfxrWaveforms.create([2,4,1,0,8,6,7,3,11,9,5,10][p.waveType] ?? 2);
        const destination=Number.isInteger(p.waveTo)&&p.waveTo>=0 ? BfxrWaveforms.create([2,4,1,0,8,6,7,3,11,9,5,10][p.waveTo]??2) : null;
        const morph=this.transition(p.morph||{start:0,end:1,curve:'Smooth'});
        let blend=p.morph?p.morph.start:0;
        let phase = 0, ic1 = 0, ic2 = 0;
        for (let i = 0; i < count; i++) {
            const t = i / (count - 1);
            if(destination)blend+=(morph(t)-blend)*.012;
            // Two millisecond smoothing avoids clicks with stepped transitions.
            for (let j = 0; j < controls.length; j++) values[j] += (envelopes[j](t) - values[j]) * 0.012;
            const [pitch, tone, vibrato, level] = values;
            const frequency = this.frequency(pitch) * Math.pow(2, Math.sin(i / rate * Math.PI * 16) * vibrato * 0.16);
            const step = frequency / (rate * 2);
            const g = Math.tan(Math.PI * this.cutoff(tone) / (rate * 2));
            const a1 = 1 / (1 + g * (g + damping));
            let sample = 0;
            // Oversample oscillator + topology-preserving state-variable filter.
            for (let sub = 0; sub < 2; sub++) {
                const source = waveform(phase, step);
                const osc = destination ? source*(1-blend)+destination(phase,step)*blend : source;
                phase = (phase + step) % 1;
                const v1 = a1 * (ic1 + g * (osc - ic2));
                const v2 = ic2 + g * v1;
                ic1 = 2 * v1 - ic1;
                ic2 = 2 * v2 - ic2;
                sample += v2 * 0.5;
            }
            const fade = Math.min(1, i / attack) * Math.min(1, (count - 1 - i) / release);
            output[i] = Math.tanh(sample * 1.4) * level * fade;
        }
        // Echo remains outside the voice envelope, so the last note can ring out.
        for (let i = 0; i < output.length; i++) {
            if (i >= delay) output[i] += output[i - delay] * feedback;
        }
        for (let i = 0; i < output.length; i++) {
            const fade = tail ? Math.min(1, (output.length - 1 - i) / 256) : 1;
            output[i] = Math.tanh(output[i]) * p.masterVolume * 0.95 * fade;
        }
        return output;
    }
}

// js/audio/SoundDSP.js
// Shared deterministic audio utilities for the specialized sound makers.
class SoundDSP {
    static rate = 44100;
    static clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    static rng(seed) {
        let state = Math.floor(seed * 4294967295) >>> 0;
        const imul = Math.imul;
        return () => {
            state = (state + 0x6D2B79F5) | 0;
            let t = imul(state ^ state >>> 15, 1 | state);
            t = t + imul(t ^ t >>> 7, 61 | t) ^ t;
            return ((t ^ t >>> 14) >>> 0) / 4294967296;
        };
    }
    static finish(buffer, volume = 0.5, options = {}) {
        let mean = 0;
        for (const value of buffer) mean += Number.isFinite(value) ? value : 0;
        mean /= Math.max(1, buffer.length);
        const fadeLength = Math.max(1, Math.min(220, Math.floor(buffer.length / 2)));
        for (let i = 0; i < buffer.length; i++) {
            const value = Number.isFinite(buffer[i]) ? buffer[i] - mean : 0;
            const fade = options.loop ? 1 : Math.min(1, i / fadeLength, (buffer.length - 1 - i) / fadeLength);
            buffer[i] = Math.tanh(value) * this.clamp(volume, 0, 1) * 0.95 * fade;
        }
        return buffer;
    }
}

// js/audio/Clonkr_DSP.js
// Damped modal resonators: an object's material determines its inharmonic modes,
// while the contact gesture supplies impacts, friction, or bouncing collisions.
class Clonkr_DSP {
    static materials = [
        {pitch:0.7, ring:0.34, brightness:0.55, ratios:[1, 2.17, 3.04, 4.61, 5.43, 6.8, 8.7, 10.3]},
        {pitch:1.55, ring:1.25, brightness:0.95, ratios:[1, 2.32, 4.25, 6.63, 9.38, 12.4, 15.8, 18.1]},
        {pitch:0.92, ring:1.6, brightness:1, ratios:[1, 1.48, 2.06, 2.63, 3.52, 4.89, 6.28, 8.13]},
        {pitch:1.12, ring:0.58, brightness:0.74, ratios:[1, 1.87, 3.22, 4.74, 6.18, 7.91, 10.2, 12.6]},
        {pitch:0.42, ring:0.16, brightness:0.2, ratios:[1, 1.99, 3.02, 4.08, 5.19, 6.31, 7.46, 8.64]}
    ];

    static render(params) {
        const value = (name, fallback, min = 0, max = 1) => SoundDSP.clamp(
            Number.isFinite(params[name]) ? params[name] : fallback, min, max);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const material = this.materials[Math.round(value('material', 0, 0, 4))];
        const action = Math.round(value('action', 0, 0, 2));
        const size = value('size', 0.5), hollow = value('hollowness', 0.35);
        const hardness = value('hardness', 0.65), damping = value('damping', 0.35);
        const duration = value('duration', 0.7, 0.1, 2);
        const decay = 0.009 + (0.022 + duration * 0.44 * material.ring) * (1 - 0.92 * damping);
        const contactEnd = action === 0 ? 0.025 : duration;
        const length = Math.ceil((contactEnd + Math.min(3.5, decay * 7)) * rate);
        const buffer = new Float32Array(length), excitation = new Float32Array(length);
        const onset = Math.round(0.006 * rate);
        const impact = (time, strength) => {
            const start = Math.round(time * rate);
            if (start >= length) return;
            // Soft strikers spread their force over a few milliseconds. A hard
            // striker approaches an impulse and excites the highest modes.
            const width = Math.max(1, Math.round((1 - hardness) * 0.0025 * rate));
            for (let j = 0; j < width && start + j < length; j++) {
                const force = width === 1 ? 1 : Math.sin(Math.PI * (j + 0.5) / width) * Math.PI / (2 * width);
                excitation[start + j] += force * strength;
            }
            const noiseLength = Math.round((0.002 + (1 - hardness) * 0.009) * rate);
            for (let j = 0; j < noiseLength && start + j < length; j++) {
                buffer[start + j] += (random() * 2 - 1) * Math.exp(-j / (noiseLength * 0.2))
                    * strength * (0.07 + hardness * 0.2);
            }
        };

        impact(onset / rate, 1);
        if (action === 1) {
            let friction = 0;
            for (let i = onset; i < Math.round(contactEnd * rate); i++) {
                const progress = (i - onset) / Math.max(1, contactEnd * rate - onset);
                friction += ((random() * 2 - 1) - friction) * (0.08 + 0.7 * hardness);
                const grain = random() < (0.002 + hardness * 0.012) ? (random() * 2 - 1) * 0.2 : 0;
                excitation[i] += (friction * 0.022 + grain) * Math.sin(Math.PI * progress) ** 0.4;
                buffer[i] += friction * (0.08 + 0.12 * hardness) * Math.sin(Math.PI * progress);
            }
        } else if (action === 2) {
            const count = Math.round(4 + duration * 7 + hardness * 7);
            for (let hit = 1; hit < count; hit++) {
                const progress = hit / count;
                const time = 0.012 + (contactEnd - 0.025) * (progress + (random() - 0.5) * 0.5 / count);
                impact(time, (0.35 + random() * 0.65) * (1 - progress * 0.6));
            }
        }

        const base = 1400 * Math.pow(2, -size * 4.4) * material.pitch;
        const modes = material.ratios.map((ratio, index) => {
            const detune = 1 + (random() - 0.5) * 0.018;
            const frequency = Math.min(rate * 0.43, base * ratio * detune);
            const angle = Math.PI * 2 * frequency / rate;
            const tau = decay / (1 + index * (0.08 + damping * 0.13));
            const radius = Math.exp(-1 / (tau * rate));
            const weight = Math.exp(-index * (0.28 + (1 - hardness) * 0.62 + (1 - material.brightness) * 0.4))
                * (index === 0 ? 1 + hollow * 1.2 : 1 - hollow * 0.35);
            return {cos:Math.cos(angle) * radius, sin:Math.sin(angle) * radius, real:0, imaginary:0, weight};
        });
        const scale = 1.4 / modes.reduce((sum, mode) => sum + mode.weight, 0);
        for (let i = onset; i < length; i++) {
            let sample = 0;
            for (const mode of modes) {
                const real = mode.real * mode.cos - mode.imaginary * mode.sin + excitation[i];
                mode.imaginary = mode.real * mode.sin + mode.imaginary * mode.cos;
                mode.real = real;
                sample += real * mode.weight;
            }
            buffer[i] += sample * scale;
        }
        return SoundDSP.finish(buffer, value('masterVolume', 0.5));
    }
}

// js/audio/Machinr_DSP.js
// Rotating parts, friction and resonant contacts; no recordings or browser state.
class Machinr_DSP {
    static render(p) {
        const rate = SoundDSP.rate;
        const count = Math.max(2, Math.round(p.duration * rate));
        const output = new Float32Array(count);
        const random = SoundDSP.rng(p.seed);
        const {sin, cos, exp, abs, min, max, PI} = Math;
        const tau = 2 * PI;
        const scale = Math.pow(2, (0.5 - p.size) * 2.6);
        const base = (35 + 230 * p.speed * p.speed) * scale * (1 - 0.32 * p.load);
        const toothRate = (5 + p.speed * 48) * (1 - p.load * 0.28);
        const attack = max(0.003, p.startTime) * rate;
        const release = max(0.006, p.stopTime) * rate;
        // Contact resonances share a material size, but alternate on an escapement.
        const ringFrequency = min(8500, (650 + 1100 * (1 - p.size)) * scale);
        const decay = exp(-1 / (rate * (0.007 + 0.035 * p.looseness)));
        const ringA = 2 * decay * cos(tau * ringFrequency / rate);
        const ringB = 2 * decay * cos(tau * ringFrequency * 0.63 / rate);
        let a1=0, a2=0, b1=0, b2=0, phase=0, teeth=0, slowNoise=0, friction=0;
        let previousTooth=-1, turn=0, contact=0, eventStrength=1;
        const rotorOffset = random() * tau;
        for (let i=0; i<count; i++) {
            const t=i/rate, progress=i/(count-1);
            const engage=min(1,i/attack), stop=min(1,(count-1-i)/release);
            const envelope=engage*stop;
            const noise=random()*2-1;
            slowNoise += (noise-slowNoise)*0.0015;
            friction += (noise-friction)*(0.09+0.5*p.roughness);
            let spin=(0.18+0.82*engage)*(0.2+0.8*stop);
            if(p.mechanism===6) spin*=1-0.7*progress;
            const wobble=1+p.roughness*(0.085*sin(tau*7.3*t+rotorOffset)+slowNoise*1.2);
            phase += tau*base*spin*wobble/rate;
            let contactRate=toothRate;
            if(p.mechanism===3) contactRate=1.3+p.speed*8;
            if(p.mechanism===4) contactRate=7+p.speed*30;
            if(p.mechanism===7) contactRate=4+p.speed*17;
            teeth += contactRate*spin*wobble/rate;
            const tooth=Math.floor(teeth);
            let kick=0;
            if(tooth!==previousTooth) {
                previousTooth=tooth;
                turn++;
                eventStrength=0.45+random()*0.55;
                kick=(0.15+p.looseness*0.7)*eventStrength;
                if(p.mechanism===3) kick=0.75;
                if(p.mechanism===4) kick*=random()>p.roughness*0.22?1:0.1;
                contact=eventStrength;
            }
            contact *= exp(-1/(rate*(0.007+0.025*p.load)));
            // Shutters use two explicit latch contacts; the door strikes at closure.
            if(p.mechanism===2) {
                kick=(i===Math.floor(rate*0.008)||i===Math.floor(count*(0.19+0.12*p.load)))?1.9:0;
            }
            if(p.mechanism===7 && i===Math.floor(count*0.88)) kick+=3.2;
            const resonantA=kick*0.14+ringA*a1-decay*decay*a2;
            const resonantB=kick*0.11+ringB*b1-decay*decay*b2;
            a2=a1; a1=resonantA; b2=b1; b1=resonantB;
            const rattle=(turn%2?resonantA:resonantB);
            const rotor=sin(phase)+0.35*sin(2*phase)+0.12*sin(5*phase);
            let sample;
            switch(p.mechanism) {
                case 1: // Teeth rubbing and slipping under load.
                    sample=0.11*rotor+0.55*rattle+friction*(0.05+0.18*p.roughness)
                        +0.11*p.load*sin(phase*3.1+3*sin(phase*0.017))*(0.5+0.5*sin(tau*1.7*t));
                    break;
                case 2:
                    sample=1.05*(resonantA+resonantB)+0.08*rotor*exp(-progress*9)
                        +friction*0.13*exp(-progress*12);
                    break;
                case 3:
                    sample=rattle*1.35+0.014*rotor+friction*contact*0.18;
                    break;
                case 4:
                    sample=0.28*rotor*(0.3+contact)+0.4*contact*friction
                        +0.21*sin(phase*0.5)*(0.4+p.load)+0.18*rattle;
                    break;
                case 5: {
                    const position=0.55+0.45*sin(tau*(1.1+p.speed*3)*t);
                    sample=(0.25*sin(phase*(3.1+p.load))+0.09*sin(phase*6.2))*position
                        +0.05*rattle+friction*(0.015+0.035*p.roughness);
                    break;
                }
                case 6:
                    sample=0.13*sin(phase*1.9+2*sin(teeth*0.38))+0.53*rattle
                        +0.08*rotor+friction*(0.015+0.09*p.roughness);
                    break;
                case 7: {
                    const creak=sin(phase*0.62+4*sin(phase*0.023));
                    sample=0.27*creak*(0.55+0.45*sin(teeth*1.4))+0.45*rattle
                        +0.14*sin(phase*0.31)+friction*p.roughness*0.1;
                    break;
                }
                default:
                    sample=0.24*rotor+0.09*sin(phase*8)*(0.25+p.load)
                        +rattle*(0.1+p.looseness*0.3)+friction*(0.015+p.roughness*0.15);
            }
            output[i]=sample*envelope;
        }
        return SoundDSP.finish(output,p.masterVolume);
    }
}

// js/audio/Jinglr_DSP.js
// A small score is saved with every jingle. Playback never invents new notes.
class Jinglr_DSP {
    static scales = [[0,2,4,5,7,9,11],[0,2,3,5,7,8,10],[0,2,4,7,9],[0,2,3,5,7,9,10]];
    static defaultPhrase = '[{"degree":0,"beats":0.5},{"degree":2,"beats":0.5},{"degree":4,"beats":0.5},{"degree":7,"beats":1}]';

    static number(value, fallback, min, max) {
        return Number.isFinite(value) ? SoundDSP.clamp(value,min,max) : fallback;
    }

    static phrase(value) {
        let notes;
        try { notes = typeof value === 'string' && value.length <= 4096 ? JSON.parse(value) : null; }
        catch (_) { notes = null; }
        if (!Array.isArray(notes) || !notes.length) notes = JSON.parse(this.defaultPhrase);
        return notes.slice(0,12).map(note => {
            const valid = note && typeof note === 'object' ? note : {};
            return {degree:valid.degree === null ? null : Math.round(this.number(valid.degree,0,-7,14)),
                beats:Math.round(this.number(valid.beats,0.5,0.25,2)*4)/4};
        });
    }

    static midi(degree, params) {
        if (degree === null) return null;
        const scale = this.scales[Math.round(this.number(params.scale,0,0,3))];
        const octave = Math.round(this.number(params.octave,4,3,6));
        const key = Math.round(this.number(params.key,0,0,11));
        const index = (degree % scale.length + scale.length) % scale.length;
        return (octave+1)*12 + key + Math.floor(degree/scale.length)*12 + scale[index];
    }

    static noteName(degree, params) {
        const midi = this.midi(degree,params);
        return midi === null ? 'Rest' : ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'][midi%12] + (Math.floor(midi/12)-1);
    }

    static schedule(params) {
        const beat = 60 / this.number(params.tempo,140,60,220);
        const swing = this.number(params.swing,0,0,0.6);
        let cursor = 0;
        const phrase = this.phrase(params.phrase);
        const events = phrase.map((note,index) => {
            // Swing redistributes each pair's time, even when its beat values differ.
            const pair = Math.floor(index/2)*2;
            const shift = phrase[pair+1] ? Math.min(phrase[pair].beats,phrase[pair+1].beats)*swing : 0;
            const duration = (note.beats + (index%2 ? -shift : shift))*beat;
            const midi = this.midi(note.degree,params);
            const event = {degree:note.degree,beats:note.beats,midi,
                frequency:midi === null ? 0 : 440*Math.pow(2,(midi-69)/12),start:cursor,duration};
            cursor += duration;
            return event;
        });
        return {events,duration:cursor};
    }

    static voice(params) {
        const instrument=Math.round(this.number(params.instrument,0,0,7));
        const seed=Math.round(this.number(params.instrumentSeed,42731,0,99999));
        const random=SoundDSP.rng((instrument*100000+seed+1)/800001);
        const attackRanges=[[0.001,0.012],[0.001,0.006],[0.001,0.009],[0.006,0.04],
            [0.001,0.012],[0.012,0.06],[0.001,0.015],[0.025,0.12]];
        const attack=attackRanges[instrument];
        // Each code describes a whole instrument, not a pitch offset or a new melody.
        return {instrument,seed,attack:attack[0]+random()*(attack[1]-attack[0]),
            release:0.6+random()*0.85,damping:0.45+random()*1.9,
            slope:0.65+random()*1.5,color:0.2+random()*0.75,
            hollow:random(),filter:1.5+random()*9,body:0.65+random()*0.35,
            modulation:0.3+random()*3.5,modRatio:1+Math.floor(random()*4),
            spread:0.001+random()*0.005,pick:0.08+random()*0.4};
    }

    static render(params) {
        const score = this.schedule(params);
        const rate = SoundDSP.rate;
        const brightness = this.number(params.brightness,0.55,0,1);
        const decay = this.number(params.decay,0.45,0,1);
        const echo = this.number(params.echo,0.12,0,0.8);
        const voice = this.voice(params), instrument=voice.instrument;
        const tail = (0.035 + decay*0.26)*voice.release;
        const delay = 60/this.number(params.tempo,140,60,220)*0.75;
        const echoTail = echo > 0 ? delay*3 : 0;
        const pcm = new Float32Array(Math.ceil((score.duration+tail+echoTail)*rate));
        // Timbre, attacks and breath have their own RNG; melody seed only chooses notes.
        const random = SoundDSP.rng((voice.seed*7+instrument*100003+1)%1000003/1000003);
        const sin = Math.sin;
        for (const note of score.events) {
            if (note.midi === null) continue;
            const start = Math.round(note.start*rate);
            const gate = note.duration*(0.52+0.38*decay)*voice.body;
            const length = Math.ceil((gate+tail)*rate);
            const strength = 0.84+random()*0.16;
            const phase = random()*Math.PI*2;
            const partials=[];
            const addPartial=(ratio,gain,falloff,offset=0)=>{
                if (note.frequency*ratio<rate*0.45) partials.push({
                    step:Math.PI*2*note.frequency*ratio/rate,gain,
                    falloff:Math.exp(-falloff*voice.damping/rate),offset});
            };
            if (instrument===0) {
                // A plucked harmonic string; bright overtones die away first.
                for(let h=1;h<=10;h++) {
                    const pick=h===1 ? 1 : 0.25+0.75*Math.abs(sin(Math.PI*h*voice.pick));
                    addPartial(h,pick*Math.pow(0.12+brightness*0.85,h-1)/Math.pow(h,voice.slope),
                        (1.5+(1-decay)*7)*Math.sqrt(h));
                }
            } else if (instrument===1) {
                [1,2+voice.color*1.1,3.8+voice.hollow*2.3,7.5+voice.color*2.5].forEach((ratio,h)=>
                    addPartial(ratio,h===0 ? 0.8 : (0.1+brightness*0.85)/Math.pow(h+1,voice.slope),
                        (0.7+(1-decay)*5)*(1+h*0.6)));
            } else if (instrument===2) {
                // A pulse of varying duty, represented by band-limited harmonics.
                const duty=0.12+voice.hollow*0.38;
                for(let h=1;h<=16;h++) addPartial(h,
                    0.8*sin(Math.PI*h*duty)/sin(Math.PI*duty)*Math.pow(0.3+brightness*0.7,h-1)/Math.pow(h,voice.slope),
                    0.45+(1-decay)*2);
            } else if (instrument===3) {
                addPartial(1,0.8,0.35+(1-decay)*1.5);
                for(let h=2;h<=5;h++) addPartial(h,brightness*voice.color*0.5/Math.pow(h-1,voice.slope),
                    (0.35+(1-decay)*1.5)*(1+h*0.15));
            } else if (instrument===4) {
                // Hammered keys mix a warm body with short, ringing tine overtones.
                for(let h=1;h<=8;h++) addPartial(h,
                    (h===1 ? 0.85 : (0.2+brightness*0.7)*(h%2 ? 0.55 : 1))/Math.pow(h,voice.slope),
                    (0.8+(1-decay)*4)*(1+h*0.3));
                addPartial(4+voice.color*0.04,brightness*voice.hollow*0.35,12+(1-decay)*12);
            } else if (instrument===5) {
                // Reed character moves between hollow odd partials and a nasal full spectrum.
                for(let h=1;h<=12;h++) {
                    const resonance=1+voice.color*Math.exp(-Math.pow((h-(2+voice.hollow*4))/2,2))*2;
                    const even=h%2 ? 1 : 0.1+voice.hollow*0.85;
                    addPartial(h,0.65*resonance*even*Math.pow(0.35+brightness*0.65,h-1)/Math.pow(h,voice.slope),
                        0.2+(1-decay)*0.8);
                }
            } else if (instrument===6) {
                // An unmodulated center holds the note underneath the changing FM spectrum.
                addPartial(1,0.28,0.5+(1-decay)*3);
            } else {
                // Paired detuned partials make a bowed ensemble without moving its center pitch.
                for(let h=1;h<=10;h++) {
                    const gain=0.32*Math.pow(0.5+brightness*0.48,h-1)/Math.pow(h,voice.slope);
                    addPartial(h*(1-voice.spread),gain,0.15+(1-decay)*0.6);
                    addPartial(h*(1+voice.spread),gain,0.15+(1-decay)*0.6,voice.color*2);
                }
            }
            const startPhase=instrument===2 ? 0 : phase;
            const attackLength=Math.min(voice.attack,gate*0.65)*rate;
            let breath=0.005*brightness*(0.3+voice.hollow);
            const breathFalloff=Math.exp(-(0.5+(1-decay)*2)*voice.damping/rate);
            const cutoff=Math.min(rate*0.44,note.frequency*(voice.filter+brightness*9));
            const filter=1-Math.exp(-Math.PI*2*cutoff/rate);
            let filtered=0;
            const fundamental=Math.PI*2*note.frequency/rate;
            // Reserve room for FM sidebands at high registers.
            const fmIndex=Math.min(voice.modulation*(0.15+brightness),Math.max(0,(rate*0.4/note.frequency-1)/voice.modRatio));
            let fmAmount=fmIndex, fmGain=0.62;
            const fmFalloff=Math.exp(-(2+(1-decay)*8)*voice.damping/rate);
            const fmGainFalloff=Math.exp(-(0.6+(1-decay)*3)*voice.damping/rate);
            for (let i=0;i<length && start+i<pcm.length;i++) {
                const time = i/rate;
                const attack = i<attackLength ? i/attackLength : 1;
                const release = time>gate ? 1-(time-gate)/tail : 1;
                let sample = 0;
                for (const partial of partials) {
                    sample += sin(partial.step*i+startPhase+partial.offset)*partial.gain;
                    partial.gain *= partial.falloff;
                }
                if (instrument===3 || instrument===5) {
                    sample += (random()*2-1)*breath;
                    breath *= breathFalloff;
                }
                if (instrument===6) {
                    sample += sin(fundamental*i+startPhase+(fmIndex*0.18+fmAmount)*sin(fundamental*i*voice.modRatio))*fmGain;
                    fmAmount*=fmFalloff; fmGain*=fmGainFalloff;
                }
                filtered+=(sample-filtered)*filter;
                pcm[start+i] += filtered*attack*release*strength;
            }
        }
        if (echo>0) {
            const dry = pcm.slice();
            for (let repeat=1;repeat<=3;repeat++) {
                const offset = Math.round(delay*repeat*rate);
                const gain = Math.pow(echo*0.58,repeat);
                for (let i=0;i+offset<pcm.length;i++) pcm[i+offset] += dry[i]*gain;
            }
        }
        return SoundDSP.finish(pcm,this.number(params.masterVolume,0.5,0,1));
    }
}

// js/audio/Squishr_DSP.js
// Liquids combine chirped bubble resonances with pressure-driven filtered noise.
// Each gesture has its own event timing, pitch contour, and deformation envelope.
class Squishr_DSP {
    static render(params) {
        const value = (name, fallback, min = 0, max = 1) => SoundDSP.clamp(
            Number.isFinite(params[name]) ? params[name] : fallback, min, max);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const texture = Math.round(value('texture', 0, 0, 5));
        const viscosity = value('viscosity', 0.6), stretch = value('stretch', 0.4);
        const pressure = value('pressure', 0.6), wetness = value('wetness', 0.75);
        const bubbleSize = value('bubbleSize', 0.55), duration = value('duration', 0.65, 0.1, 3);
        const release = 0.06 + viscosity * 0.16 + stretch * 0.13;
        const length = Math.ceil((duration + release) * rate);
        const buffer = new Float32Array(length);
        const base = 1650 * Math.pow(2, -bubbleSize * 3.8);
        const amplitude = 0.45 + pressure * 0.7;
        const onset = 0.008;
        const events = [];
        const addBubble = (start, strength, pitch = 1, life = 1) => {
            const seconds = (0.026 + viscosity * 0.065 + stretch * 0.13) * life;
            events.push({start:Math.round(start * rate), length:Math.round(seconds * rate),
                frequency:base * pitch * (0.84 + random() * 0.32), strength, phase:random() * 0.2});
        };

        if (texture === 1) {
            const count = Math.max(1, Math.round(duration * (2 + pressure * 7)));
            for (let i = 0; i < count; i++) addBubble(onset + i * duration * 0.85 / count,
                0.7 + random() * 0.3, 0.8 + random() * 0.4, 1.1);
        } else if (texture === 2) {
            // Suction builds slowly, then breaks into one rounded release pop.
            addBubble(duration * 0.76, 1.2, 0.75, 1.5);
            addBubble(duration * 0.87, 0.55, 1.3, 0.7);
        } else if (texture === 3) {
            for (let i = 0; i < 7; i++) addBubble(onset + random() * duration * 0.34,
                0.4 + random() * 0.45, 0.6 + random() * 1.1, 0.6 + random() * 0.6);
        } else if (texture === 4) {
            const count = Math.max(1, Math.round(duration * (3 + pressure * 3)));
            for (let i = 0; i < count; i++) {
                const time = onset + i * duration * 0.82 / count;
                addBubble(time, 1, 0.62, 1.4);
                addBubble(time + 0.035, 0.45, 1.35, 0.7);
            }
        } else {
            const count = Math.max(2, Math.round(duration * (5 + pressure * 10)));
            for (let i = 0; i < count; i++) addBubble(onset + i * duration * 0.88 / count,
                0.3 + random() * 0.5, texture === 5 ? 0.7 : 0.5 + random() * 0.8,
                texture === 5 ? 2 : 0.65 + random() * 0.65);
        }

        let lowNoise = 0, smoothNoise = 0, bodyPhase = 0, previous = 0;
        const cutoff = 180 + (1 - viscosity) * 3800 + pressure * 500;
        const filter = 1 - Math.exp(-Math.PI * 2 * cutoff / rate);
        for (let i = 0; i < length; i++) {
            const time = i / rate, progress = Math.min(1, time / duration);
            const tail = time <= duration ? 1 : Math.exp(-(time - duration) / (release * 0.2));
            const noise = random() * 2 - 1;
            lowNoise += (noise - lowNoise) * filter;
            smoothNoise += (lowNoise - smoothNoise) * filter;
            let envelope;
            if (texture === 2) envelope = Math.sin(Math.PI * Math.min(1, progress / 0.85)) ** 2;
            else if (texture === 3) envelope = Math.exp(-progress * (5 - viscosity * 2));
            else if (texture === 4) envelope = (0.4 + 0.6 * Math.sin(progress * Math.PI * (3 + pressure * 3)) ** 2) * (1 - progress * 0.6);
            else envelope = Math.sin(Math.PI * progress) ** 0.55;
            const attack = Math.min(1, time / 0.009);
            const bodyFrequency = base * (texture === 5 ? 0.27 : 0.16)
                * (1 + Math.sin(time * (12 + pressure * 20)) * stretch * 0.3)
                * (texture === 2 ? 1.6 - progress : 1 - progress * stretch * 0.45);
            bodyPhase += Math.PI * 2 * bodyFrequency / rate;
            const body = Math.sin(bodyPhase + Math.sin(bodyPhase * 0.5) * stretch)
                * (texture === 5 ? 0.4 : 0.13) * (0.25 + viscosity * 0.75);
            const rasp = (smoothNoise * (0.6 + wetness * 0.45) + (lowNoise - previous) * (1 - viscosity) * 0.25);
            const noiseLevel = texture === 1 ? 0.015 : texture === 5 ? 0.14 : texture === 3 ? 1.1 : 0.7;
            const bodyLevel = texture === 1 ? 0.03 : 1;
            buffer[i] = (rasp * noiseLevel + body * bodyLevel) * envelope * tail * amplitude * attack;
            previous = lowNoise;
        }

        for (const event of events) {
            let phase = event.phase;
            for (let j = 0; j < event.length && event.start + j < length; j++) {
                const progress = j / event.length;
                let glide;
                if (texture === 2 || texture === 4) glide = 1.65 - progress * (1.1 + stretch * 0.3);
                else if (texture === 5) glide = 1 + Math.sin(progress * Math.PI * (3 + stretch * 5)) * stretch * 0.6;
                else glide = 0.65 + progress * (0.8 + pressure * 1.5) + Math.sin(progress * Math.PI) * stretch * 0.5;
                phase += Math.PI * 2 * event.frequency * glide / rate;
                const envelope = Math.min(1, j / (rate * 0.0015)) * Math.exp(-progress * (5 - viscosity * 2))
                    * Math.min(1, (1 - progress) * 15);
                const rounded = Math.sin(phase) + Math.sin(phase * 2) * (1 - viscosity) * 0.13;
                buffer[event.start + j] += rounded * envelope * event.strength * amplitude * (0.25 + wetness * 0.7);
            }
        }
        return SoundDSP.finish(buffer, value('masterVolume', 0.5));
    }
}

// js/audio/Mixr_DSP.js
// Two independently saved sounds, played together at a constant total gain.
class Mixr_DSP {
    static render(p, renderSource = source => Mixr.render_source(source, Number.isFinite(source.renderSeed) ? source.renderSeed : p.seed)) {
        let sources;
        try { sources = JSON.parse(p.sources); } catch { sources = []; }
        if (!Array.isArray(sources)) sources = [];
        const pcm = sources.slice(0, 2).map(source => source ? renderSource(source) : null);
        const balance = Number.isFinite(p.balance) ? SoundDSP.clamp(p.balance, 0, 1) : 0.5;
        const volume = Number.isFinite(p.masterVolume) ? SoundDSP.clamp(p.masterVolume, 0, 1) : 0.5;
        const out = new Float32Array(Math.min(SoundDSP.rate * 12, Math.max(4410, ...pcm.map(a => a ? a.length : 0))));
        const both = pcm[0] && pcm[1];
        for (let slot = 0; slot < pcm.length; slot++) {
            if (!pcm[slot]) continue;
            const gain = (both ? (slot === 0 ? 1 - balance : balance) : 1) * volume * 2;
            for (let i = 0; i < pcm[slot].length && i < out.length; i++) out[i] += pcm[slot][i] * gain;
        }
        for (let i = 0; i < out.length; i++) {
            out[i] = Number.isFinite(out[i]) ? SoundDSP.clamp(out[i], -1, 1) : 0;
            if (i > out.length - 128) out[i] *= (out.length - 1 - i) / 127;
        }
        return out;
    }
}

// js/audio/Crittr_DSP.js
// Nonverbal calls: pulsed breath drives three moving throat resonances.
class Crittr_DSP {
    static render(p) {
        const {sin, cos, exp, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low=0, high=1) => Number.isFinite(p[name])
            ? min(high,max(low,p[name])) : fallback;
        const rate = SoundDSP.rate, tau = PI*2;
        const duration = value('duration',1.2,0.15,5);
        const output = new Float32Array(round(duration*rate));
        const volume = value('masterVolume',0.5);
        if (volume === 0) return SoundDSP.finish(output,0);
        const random = SoundDSP.rng(value('seed',0.5));
        const voice = round(value('voice',0,0,7));
        const pitch = 45*2**(5*value('pitch',0.45));
        const size = value('size',0.45), morph = value('morph',0.45);
        const breath = value('breath',0.15), growl = value('growl',0.2);
        const flutter = value('flutter',0.2), contour = value('contour',0.25,-1,1);
        const calls = round(value('calls',2,1,12));
        const slot = output.length/calls, active = slot*(1-value('gap',0.2,0,0.85));
        const attack = max(40,active*(voice===6?0.025:voice===7?0.13:0.09)), release = max(80,active*0.28);
        const scale = 2**((0.5-size)*2.8);
        const anatomies = [[550,1260,2550],[820,2100,3900],[360,950,1840],
            [1100,2800,4700],[430,1500,3200],[670,1740,3550],[430,1150,2450],[700,1900,3100]];
        const frequencies = anatomies[voice].map(frequency => min(10000,frequency*scale));
        const radii = [exp(-PI*100/rate),exp(-PI*160/rate),exp(-PI*230/rate)];
        const coefficients = [0,0,0], y1 = [0,0,0], y2 = [0,0,0];
        const radiiSquared = radii.map(radius => radius*radius);
        const gains = radii.map(radius => (1-radius)*0.95);
        const callMotion = Array.from({length:calls},() => random()*2-1);
        const flutterRate = 7+flutter*38, flutterStep = tau*flutterRate/rate;
        const duty = [0.24,0.12,0.3,0.07,0.38,0.1,0.2,0.28][voice];
        let phase = random()*tau, flutterPhase = random()*tau;
        let previous=0, previous2=0, noiseLow=0;
        for (let i=0;i<output.length;i++) {
            const call = min(calls-1,floor(i/slot)), local = i-call*slot;
            const position = min(1,local/active);
            const envelope = max(0,min(1,local/attack,(active-local)/release));
            const tremor = sin(flutterPhase);
            flutterPhase += flutterStep;
            let bend = contour*((position-0.5)*1.9+callMotion[call]*0.3);
            if (voice===6) bend += 0.5*exp(-position*13)-position*0.3;
            if (voice===7) bend += 0.5*sin(PI*min(1,position*1.35))-0.3*position;
            phase += tau*pitch*exp(bend*0.69314718056)*(1+flutter*0.045*tremor)/rate;
            const cycle = phase/tau-floor(phase/tau);
            const pulse = cycle<duty ? 0.5-0.5*cos(tau*cycle/duty) : 0;
            const noise = random()*2-1;
            noiseLow += (noise-noiseLow)*0.06;
            let excitation = (pulse-duty*0.5)*3.4;
            if (voice===1) excitation += 0.22*sin(phase*2+0.8*sin(phase));
            if (voice===2) excitation *= 0.7+0.3*sin(phase*0.5);
            if (voice===3) excitation *= 0.6+0.4*sin(phase*1.47);
            if (voice===4) excitation = 0.48*sin(phase)+excitation*0.3;
            if (voice===5) excitation += 0.2*sin(phase*2.71);
            if (voice===6) excitation = excitation*(0.85+0.15*sin(phase*0.5))+noise*0.65*exp(-position*20);
            if (voice===7) excitation += 0.18*sin(phase*2)+0.09*sin(phase*3);
            excitation = excitation*(1-breath*0.8)+noise*breath*0.9;
            // Change resonances at control rate; oscillator pitch stays independent.
            if ((i&31)===0) {
                const opening = morph*(sin(PI*position)+0.3*callMotion[call]);
                coefficients[0] = 2*radii[0]*cos(tau*min(11000,frequencies[0]*(1+opening*0.65))/rate);
                coefficients[1] = 2*radii[1]*cos(tau*min(11000,frequencies[1]*(1-opening*0.23))/rate);
                coefficients[2] = 2*radii[2]*cos(tau*min(11000,frequencies[2]*(1+opening*0.17))/rate);
                if (voice===6 || voice===7) {
                    // Bark opens rapidly; meow moves from a nasal /m/ through /a/ into /u/.
                    const mouth = voice===6 ? exp(-position*5) : sin(PI*position)**1.4;
                    coefficients[0] = 2*radii[0]*cos(tau*min(11000,frequencies[0]*(0.58+morph*mouth*0.95))/rate);
                    coefficients[1] = 2*radii[1]*cos(tau*min(11000,frequencies[1]*(1-morph*position*0.58))/rate);
                }
            }
            let resonant=0;
            for (let band=0;band<3;band++) {
                const sample = gains[band]*(excitation-previous2)+coefficients[band]*y1[band]-radiiSquared[band]*y2[band];
                y2[band]=y1[band]; y1[band]=sample;
                resonant += sample*(band===0?1.15:band===1?0.85:0.5);
            }
            previous2=previous; previous=excitation;
            const subharmonic = growl*(0.28*sin(phase*0.5)+0.1*sin(phase/3))*(0.85+noiseLow*0.7);
            const throat = resonant*1.65+0.12*(1-breath)*sin(phase)+subharmonic;
            const trill = 1-flutter*0.42+flutter*0.42*tremor;
            const articulation = voice===6 ? exp(-position*4.5) : voice===7 ? 0.75+0.25*sin(PI*position) : 1;
            output[i] = throat*envelope*trill*articulation;
        }
        return SoundDSP.finish(output,volume);
    }
}

// js/audio/Birdr_DSP.js
// Two syringeal oscillators, beak resonances and a syllable-level breath schedule.
class Birdr_DSP {
    static render(p) {
        const {sin,cos,exp,PI,min,max,round} = Math;
        const value = (name,fallback,low=0,high=1) => Number.isFinite(p[name]) ? min(high,max(low,p[name])) : fallback;
        const rate=SoundDSP.rate,tau=2*PI,duration=value('duration',0.8,0.15,5);
        const output=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if (volume===0) return SoundDSP.finish(output,0);
        const random=SoundDSP.rng(value('seed',0.5)),voice=round(value('voice',0,0,4));
        const count=round(value('syllables',3,1,16)),gap=value('gap',0.3,0,0.85);
        const pitch=180*2**(value('pitch',0.58)*4.8),sweep=value('sweep',-0.3,-1,1),arch=value('arch',0.45,-1,1);
        const trill=value('trill',0.15),trillRate=5+value('trill_rate',0.4)*65;
        const duet=value('duet',0.1),rasp=value('rasp',0.04),breath=value('breath',0.03);
        const rhythm=value('rhythm',0.12),variation=value('variation',0.25);
        // Repeat a contour with alternating answers and seeded drift, rather than choosing unrelated notes.
        const weights=Array.from({length:count},()=>1+rhythm*(random()-0.5)*1.1);
        const total=weights.reduce((a,b)=>a+b,0);
        let offset=0;
        const syllables=weights.map((weight,index)=>{
            const length=weight/total*output.length;
            const result={start:offset,active:max(1,length*(1-gap)),
                shift:variation*((index%2?-0.6:0.15)+(random()-0.5)*0.2),
                curvature:1+variation*(random()-0.5)*0.5,phase:random()*tau};
            offset+=length; return result;
        });
        let phase=random()*tau,second=random()*tau,noiseLow=0,call=0;
        const radii=[exp(-PI*260/rate),exp(-PI*480/rate)],y1=[0,0],y2=[0,0];
        const centers=voice===3?[850,1850]:[1550,3200];
        const coeff=centers.map((f,i)=>2*radii[i]*cos(tau*f/rate));
        for(let i=0;i<output.length;i++) {
            while(call<count-1 && i>=syllables[call+1].start) call++;
            const syllable=syllables[call],local=i-syllable.start,u=min(1,local/syllable.active);
            const attack=max(35,syllable.active*(voice===4?0.18:0.065));
            const release=max(70,syllable.active*(voice===3?0.4:0.2));
            let envelope=max(0,min(1,local/attack,(syllable.active-local)/release));
            envelope*=voice===4?sin(PI*u)**0.6:0.88+0.12*sin(PI*u);
            const tremor=sin(tau*trillRate*local/rate+syllable.phase);
            const contour=sweep*(u-0.5)*1.8+arch*sin(PI*u)*syllable.curvature+syllable.shift;
            const irregular=rasp*(0.035*sin(phase*0.47)+0.022*sin(second*0.31));
            const frequency=min(10500,pitch*2**(contour+trill*0.2*tremor+irregular));
            phase+=tau*frequency/rate;
            second+=tau*min(11500,frequency*(1.12+0.15*sin(PI*u)+duet*0.35))/rate;
            const noise=random()*2-1;
            noiseLow+=(noise-noiseLow)*0.13;
            const modulation=voice===1?duet*1.15*sin(second):0;
            let source=sin(phase+modulation);
            if(voice===2) source=0.7*sin(phase+0.8*sin(phase))+0.23*sin(phase*2)+0.12*sin(phase*3);
            if(voice===3) source=0.55*sin(phase+1.3*sin(phase))+0.3*sin(phase*0.5)+rasp*noiseLow;
            if(voice===4) source=0.88*sin(phase)+0.1*sin(phase*2);
            source+=duet*0.28*sin(second)+rasp*0.2*sin(phase*0.5)*(0.65+0.35*sin(phase*0.19));
            let resonant=0;
            for(let band=0;band<2;band++) {
                const sample=(1-radii[band])*source+coeff[band]*y1[band]-radii[band]**2*y2[band];
                y2[band]=y1[band];y1[band]=sample;resonant+=sample;
            }
            if(voice===2 || voice===3) source=source*0.62+resonant*0.85;
            source=source*(1-breath*0.45)+breath*(noise-noiseLow)*0.25;
            const pulse=1-trill*0.35+trill*0.35*tremor;
            output[i]=source*envelope*pulse*0.65;
        }
        return SoundDSP.finish(output,volume);
    }
}

// js/audio/Signlr_DSP.js
// Packet scheduling with frequency/phase coding, dropouts and radio echoes.
class Signlr_DSP {
    static render(p) {
        const {sin, exp, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low=0, high=1) => Number.isFinite(p[name])
            ? min(high,max(low,p[name])) : fallback;
        const rate = SoundDSP.rate, tau = 2*PI;
        const duration = value('duration',1.4,0.15,5);
        const output = new Float32Array(round(duration*rate));
        const volume = value('masterVolume',0.5);
        if (volume===0) return SoundDSP.finish(output,0);
        const seed = value('seed',0.5), random = SoundDSP.rng(seed);
        const encoding = round(value('encoding',0,0,4));
        if(encoding===4)return this.pings(p);
        const carrier = 90*2**(value('carrier',0.55)*5.7);
        const deviation = value('deviation',0.35), drift = value('drift',0,-1,1);
        const interference = value('interference',0.08), corruption = value('corruption',0.08);
        const echo = value('echo',0.15), symbols = 4+176*value('symbols',0.4)**2;
        const symbolSamples = rate/symbols;
        const packets = round(value('packets',3,1,12));
        const slot = output.length/packets, active = slot*(1-value('gap',0.25,0,0.85));
        const edge = min(rate*0.005,active*0.12);
        const symbolEdge = min(rate*0.0007,symbolSamples*0.06);
        const delayA = round(rate*(0.073+seed*0.041)), delayB = round(delayA*1.79);
        let phase=random()*tau, lastSymbol=-1, lastPacket=-1, bit=1, symbolGain=1;
        let noiseLow=0, radioLow=0, phaseCode=0, scramble=0;
        let carrierNow=carrier*2**(-drift*0.5);
        const driftStep = 2**(drift/output.length);
        const heterodyneStep = tau*(carrier*1.013+37)/rate;
        let heterodyne=random()*tau;
        for(let i=0;i<output.length;i++) {
            const packet=min(packets-1,floor(i/slot)), local=i-packet*slot;
            const symbol=floor(local/symbolSamples), symbolPosition=local-symbol*symbolSamples;
            const unit=symbolPosition/symbolSamples;
            if(packet!==lastPacket || symbol!==lastSymbol) {
                lastPacket=packet; lastSymbol=symbol;
                // A four-symbol sync word precedes the seeded payload in every packet.
                bit=symbol<4 ? ((symbol+packet)%2?1:-1) : (random()<0.5?-1:1);
                symbolGain=random()<corruption*0.85?0.025:1;
                phaseCode=bit>0?0:PI;
                scramble=corruption*(random()*2-1);
            }
            let frequency=carrierNow;
            if(encoding===0) frequency*=2**(deviation*bit*0.7+scramble*0.2);
            if(encoding===2) frequency*=2**(deviation*(1-unit*2)+scramble*0.2);
            if(encoding===3) frequency*=1+deviation*0.3*bit;
            phase+=tau*min(14000,max(30,frequency))/rate;
            carrierNow*=driftStep;
            heterodyne+=heterodyneStep;
            const noise=random()*2-1;
            noiseLow+=(noise-noiseLow)*0.08;
            let encoded;
            if(encoding===1) encoded=sin(phase+phaseCode*(0.25+deviation*0.75));
            else if(encoding===2) encoded=sin(phase)*exp(-unit*(5+deviation*5));
            else if(encoding===3) encoded=sin(phase)*(0.62+0.38*sin(phase*0.037+bit));
            else encoded=sin(phase)+0.08*deviation*sin(phase*2);
            const packetEnvelope=max(0,min(1,local/edge,(active-local)/edge));
            const bitEnvelope=encoding===2 ? min(1,symbolPosition/symbolEdge)
                : 0.88+0.12*min(1,symbolPosition/symbolEdge,(symbolSamples-symbolPosition)/symbolEdge);
            const radio=(noise-noiseLow)*0.22+sin(heterodyne)*0.14;
            const squelch=0.4+0.6*packetEnvelope;
            let sample=encoded*0.52*symbolGain*packetEnvelope*bitEnvelope+radio*interference*squelch;
            // A narrow receiver rolls off the roughest static in radio mode.
            radioLow+=(sample-radioLow)*0.3;
            if(encoding===3) sample=radioLow;
            if(i>=delayA) sample+=output[i-delayA]*echo*0.38;
            if(i>=delayB) sample-=output[i-delayB]*echo*0.17;
            output[i]=sample;
        }
        return SoundDSP.finish(output,volume);
    }
    static pings(p) {
        const rate=SoundDSP.rate,tau=Math.PI*2;
        const number=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const duration=number('duration',1.4,.15,5),packets=Math.round(number('packets',2,1,12));
        const out=new Float32Array(Math.round(duration*rate));
        const rng=SoundDSP.rng(number('seed',.5));
        const root=170*2**(number('carrier',.55)*4.1),color=number('deviation',.15);
        const fall=number('gap',.5,0,.85),echo=number('echo',.4),drift=number('drift',0,-1,1);
        // Each seed describes one struck resonator, shared by the whole scan.
        const ratios=[1,2.01+rng()*.12,3.1+rng()*1.7,5.2+rng()*2.2];
        const weights=[.8,.06+color*.28,.03+color*.17,.02+color*.1];
        const ring=.045+(1-fall)*.6,step=duration/packets;
        const phases=ratios.map(()=>rng()*tau);
        for(let packet=0;packet<packets;packet++) {
            const start=Math.round(packet*step*rate),frequency=root*2**(drift*packet/Math.max(1,packets-1));
            for(let i=0;i<Math.min(rate*(ring*6),out.length-start);i++) {
                const t=i/rate,attack=1-Math.exp(-t/.0007);
                let sample=0;
                for(let h=0;h<ratios.length;h++) {
                    if(frequency*ratios[h]>18000)continue;
                    const phase=tau*frequency*ratios[h]*(t+color*.0008*(1-Math.exp(-t/.006)));
                    sample+=Math.sin(phase+phases[h])*weights[h]*Math.exp(-t*(1+h*1.4)/ring);
                }
                sample*=attack*.7;
                out[start+i]+=sample;
                for(let repeat=1;repeat<=3;repeat++) {
                    const target=start+i+Math.round(rate*(.062+number('seed',.5)*.055)*repeat);
                    if(target<out.length)out[target]+=sample*(echo*.52)**repeat;
                }
            }
        }
        return SoundDSP.finish(out,number('masterVolume',.5));
    }

}

// js/audio/Fractr_DSP.js
// A break is a shower of brief fracture bursts, then rough shard contacts.
// Only the explicitly stylized Crystal and Pixel materials sustain tuned modes.
class Fractr_DSP {
    static materials = [
        {pitch:1.65, ring:0.22, noise:1.7, cutoff:11000, grit:0.28, ratios:[1, 2.71, 4.83]}, // Glass
        {pitch:0.84, ring:0.15, noise:2.1, cutoff:6500, grit:0.6, ratios:[1, 1.91, 3.77]}, // Ice
        {pitch:1.05, ring:1.75, noise:0.025, cutoff:10000, grit:0, ratios:[1, 1.505, 2.014]}, // Crystal
        {pitch:0.17, ring:0.08, noise:3.8, cutoff:1700, grit:1, ratios:[1, 1.63, 2.42]}, // Stone
        {pitch:1.0, ring:0.6, noise:0.015, cutoff:10000, grit:0, ratios:[1, 2, 4]}, // Pixel
        {pitch:0.65, ring:0.26, noise:1.8, cutoff:7000, grit:0.42, ratios:[1, 2.39, 5.17]}, // Armor
        {pitch:0.39, ring:0.1, noise:2.8, cutoff:3800, grit:0.45, ratios:[1, 1.82, 3.03]}, // Bone
        {pitch:0.55, ring:0.015, noise:2.8, cutoff:5100, grit:0.65, ratios:[1, 1.77, 3.11]} // Biscuit
    ];

    static render(p) {
        const {round, min, max, pow, exp, sin, cos, PI} = Math;
        const value = (name, fallback, low = 0, high = 1) => SoundDSP.clamp(
            Number.isFinite(p[name]) ? p[name] : fallback, low, high);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const duration = value('duration', 1.8, 0.15, 6);
        const output = new Float32Array(round(duration * rate));
        const materialIndex = round(value('material', 0, 0, 7));
        const material = this.materials[materialIndex];
        const tuned = materialIndex === 2 || materialIndex === 4;
        const fragments = round(value('fragments', 32, 3, 96));
        const size = value('fragmentSize', 0.4), spread = value('spread', 0.6);
        const stress = value('stress', 0.4), fracture = value('fracture', 0.75);
        const decay = value('decay', 0.4), gravity = value('gravity', 0.5), bounce = value('bounce', 0.4);
        const cascadeTime = duration * (0.012 + spread * 0.72) * (1 - gravity * 0.6);
        const gain = 1.45 * value('shards',0.35) / pow(fragments, 0.3), tau = 2 * PI;
        const bounceCount = round(bounce * 4);

        for (let shard = 0; shard < fragments; shard++) {
            const shardSize = max(0, min(1, size + (random() - 0.5) * 0.26));
            const progress = (shard + random() * 0.65) / fragments;
            let time = 0.006 + cascadeTime * pow(progress, 0.75 + 0.7 * gravity);
            if (materialIndex === 4) time = round(time * 48) / 48 + 0.006;
            const start = round(time * rate);
            let frequency = 2700 * pow(2, -shardSize * 4.5) * material.pitch * (0.65 + 0.7 * random());
            if (materialIndex === 4) frequency = 110 * pow(2, round(12 * Math.log2(frequency / 110)) / 12);
            const ringTime = (0.006 + decay * 0.23) * material.ring * (0.8 + random() * 0.4);
            const contactTime = tuned ? 0.0025 : 0.0018 + (0.004 + decay * 0.025) * (0.4 + shardSize) * (0.7 + material.grit);
            const noiseRadius = exp(-1 / (rate * contactTime));
            const crackRadius = exp(-1 / (rate * (0.0003 + shardSize * 0.00065)));
            const cutoff = material.cutoff * pow(2, -shardSize * 1.6);
            const dustFilter = 1 - exp(-tau * cutoff / rate);
            const bodyFilter = 1 - exp(-tau * (130 + 1700 * (1 - shardSize) * material.pitch) / rate);
            const strength = gain * (0.55 + random() * 0.65) * (1 - progress * 0.3);
            const flight = (0.045 + 0.34 * (1 - gravity)) * (0.4 + 0.6 * shardSize);
            const contacts = [{sample:start, strength}];
            let nextTime = time, nextFlight = flight, nextStrength = strength;
            for (let j = 0; j < bounceCount; j++) {
                nextTime += nextFlight;
                nextFlight *= 0.43 + bounce * 0.24;
                nextStrength *= 0.27 + bounce * 0.42;
                contacts.push({sample:round(nextTime * rate), strength:nextStrength});
            }
            const end = min(output.length, contacts[contacts.length - 1].sample + round(max(ringTime, contactTime) * 7 * rate));
            const modes = material.ratios.map((ratio, index) => {
                const angle = tau * min(11000, frequency * ratio) / rate;
                const radius = exp(-(1 + index * 0.55) / (ringTime * rate));
                return {c:cos(angle) * radius, s:sin(angle) * radius};
            });
            // Unrolled three-mode rotators keep the busiest 96-shard cascades cheap.
            const a = modes[0], b = modes[1], c = modes[2];
            let ar=0, ai=0, br=0, bi=0, cr=0, ci=0, noiseEnvelope=0, nextContact=0, dust=0, body=0;
            let crackEnvelope=0, crackLeft=0, nextCrack=0, contactStrength=0;
            for (let i = start; i < end; i++) {
                if (nextContact < contacts.length && i === contacts[nextContact].sample) {
                    const hit = contacts[nextContact++].strength;
                    const modeGain = tuned ? 1 : 0.12;
                    ar += hit * modeGain; br += hit * modeGain * 0.44; cr += hit * modeGain * 0.24;
                    noiseEnvelope += hit * material.noise * (tuned ? 1 : 0.58);
                    // An initial split has several tiny failures; later contacts scrape once.
                    contactStrength = hit;
                    crackLeft = tuned ? 0 : (nextContact === 1 ? 3 + round(shardSize * 4) : 1);
                    nextCrack = i;
                }
                if (crackLeft > 0 && i === nextCrack) {
                    crackEnvelope += contactStrength * (0.5 + random() * 0.9);
                    nextCrack += 5 + round(random() * (25 + shardSize * 100));
                    crackLeft--;
                }
                const an = ar * a.c - ai * a.s;
                ai = ar * a.s + ai * a.c; ar = an;
                const bn = br * b.c - bi * b.s;
                bi = br * b.s + bi * b.c; br = bn;
                const cn = cr * c.c - ci * c.s;
                ci = cr * c.s + ci * c.c; cr = cn;
                const noise = random() * 2 - 1;
                dust += (noise - dust) * dustFilter;
                body += (noise - body) * bodyFilter;
                const rough = dust + body * material.grit;
                output[i] += (ar + br + cr) * 0.52 + rough * noiseEnvelope
                    + (dust - body * 0.5) * crackEnvelope;
                noiseEnvelope *= noiseRadius;
                crackEnvelope *= crackRadius;
            }
        }
        // The parent object fails before its loose fragments land. Bipolar stress
        // releases have finite width: sharp tensile snaps, not a sustained hiss.
        // Their clusters branch in time, with a slower mass response underneath.
        const structuralRandom = SoundDSP.rng(value('seed', 0.5) * 0.79 + 0.137);
        const splitTime = 0.011 + stress * 0.029;
        const widths = [0.00012, 0.00065, 0.0002, 0.0022, 0.00015, 0.00023, 0.0011, 0.00022];
        const mass = [0.06, 0.9, 0.08, 1, 0.02, 0.35, 1.3, 0.15][materialIndex];
        const width = widths[materialIndex] * (0.7 + size * 0.8);
        const splitGain = fracture * (tuned ? 0.25 : materialIndex===7 ? 2.2 : 3.4);
        const branches = materialIndex===7 ? 34 + round(size*28) : materialIndex===6 ? 5 : 7 + round(size * 9);
        for (let branch = 0; branch < branches; branch++) {
            const u = branch / branches;
            const branchSpan = materialIndex===7 ? 0.065 + stress*0.07 : materialIndex===6 ? 0.017 : materialIndex===1 ? 0.045 + stress*0.025 : 0.022 + stress*0.035;
            const delay = branch === 0 ? 0 : 0.001 + pow(u, 1.6) * branchSpan * (0.75+structuralRandom()*0.5);
            const start = round((splitTime + delay) * rate);
            const release = width * (0.7 + structuralRandom() * 0.9);
            const weight = splitGain * (branch === 0 ? 1 : 0.25 + 0.4 * (1 - u)) * (0.75 + structuralRandom()*0.5);
            const length = min(output.length - start, round((release * 9 + 0.009 * mass) * rate));
            let gritLow = 0, massGrit = 0;
            const gritRate = 1 - exp(-tau * material.cutoff * 0.55 / rate);
            for (let j = 0; j < length; j++) {
                const t = j / rate, q = t / release;
                gritLow += gritRate * (structuralRandom() * 2 - 1 - gritLow);
                const tensile = (1 - q) * exp(-q);
                const tearing = gritLow * exp(-t / (release * 3)) * 0.55;
                const bodyQ = t / (0.002 + mass * 0.004);
                massGrit += 0.12 * (structuralRandom()*2-1-massGrit);
                const body = ((1 - bodyQ) + massGrit*(materialIndex===3 || materialIndex===6 ? 6 : 1.2)) * exp(-bodyQ) * mass * 0.95;
                output[start + j] += weight * (tensile + tearing + body);
            }
        }
        if (!tuned && stress > 0) {
            // Intermittent pre-failure strain; no ringing musical mode.
            let slow = 0, fast = 0;
            const end = min(output.length, round(splitTime * rate));
            for (let i = round(0.005 * rate); i < end; i++) {
                const u = i / end, noise = structuralRandom() * 2 - 1;
                slow += 0.006 * (noise - slow); fast += 0.055 * (noise - fast);
                const stutter = pow(0.5 + 0.5 * sin(u * (36 + materialIndex * 9)), 5);
                output[i] += (fast - slow) * stutter * stress * u * 2.5;
            }
        }
        return SoundDSP.finish(output, value('masterVolume', 0.5));
    }
}

// js/audio/Riftr_DSP.js
// A four-line feedback delay network with an orthogonal scattering junction.
// Fractional moving taps bend the field; serial allpasses disperse it in time.
class Riftr_DSP {
    static render(p) {
        const {sin, cos, exp, pow, floor, round, min, max, PI} = Math;
        const value = (name, fallback, low = 0, high = 1) => SoundDSP.clamp(
            Number.isFinite(p[name]) ? p[name] : fallback, low, high);
        const rate = SoundDSP.rate, random = SoundDSP.rng(value('seed', 0.5));
        const duration = value('duration', 1.8, 0.15, 6), count = round(duration * rate);
        const output = new Float32Array(count), excitation = round(value('excitation', 0, 0, 4));
        const volume = value('masterVolume', 0.5);
        if (volume === 0) return SoundDSP.finish(output, 0);
        const pitch = value('pitch', 0.45), bend = value('bend', -0.2, -1, 1), space = value('space', 0.5);
        const feedback = value('feedback', 0.65) * 0.955;
        const dispersion = value('dispersion', 0.55), motion = value('motion', 0.3);
        const field = value('field', 0.7), reverse = value('reverse', 0);
        const tau = 2 * PI, basePitch = 55 * pow(2, pitch * 5.8);
        const pitchStep = pow(2, bend * 3 / count);
        const baseDelay = (0.003 + space * space * 0.095) * rate;
        const ratios = [0.719, 1, 1.337, 1.731];
        const lines = ratios.map((ratio, index) => {
            const delay = max(7, baseDelay * ratio);
            const depth = motion * delay * 0.09;
            const step = tau * (0.17 + motion * 2.3) * (1 + index * 0.13) / rate;
            const phase = random() * tau;
            return {buffer:new Float32Array(Math.ceil(delay + depth + 3)), delay, depth, index:0,
                real:cos(phase), imag:sin(phase), c:cos(step), s:sin(step), filter:0, read:0};
        });
        const allpasses = [0.0023, 0.0051, 0.0113, 0.0197].map(seconds => ({
            buffer:new Float32Array(max(1, round(seconds * rate * (0.3 + space) * (0.1 + dispersion)))), index:0
        }));
        const apGain = 0.15 + dispersion * 0.59;
        const damping = 0.48 + (1 - dispersion) * 0.4;
        const pulseRadius = exp(-1 / (rate * (0.015 + space * 0.025)));
        const tearRadius = exp(-1 / (rate * (0.025 + duration * 0.16)));
        let phase=0, increment=tau*basePitch/rate, pulse=1, tear=1, noiseLow=0;
        const phaseOffset = random() * tau;
        let packet=0, packetEnvelope=0;
        const packetStep = (8 + motion * 28) / rate;
        const packetRadius = exp(-1 / (rate * 0.013));
        for (let i = 0; i < count; i++) {
            const progress = i / (count - 1);
            phase += increment; increment *= pitchStep;
            const noise = random() * 2 - 1;
            noiseLow += (noise - noiseLow) * 0.12;
            const carrier = sin(phase + 0.55 * sin(phase * 1.417 + phaseOffset));
            let input;
            switch (excitation) {
                case 1: {
                    const arc = max(0, sin(PI * min(1, progress / 0.72)));
                    input = (carrier * 0.65 + sin(phase * 0.498) * 0.28 + noiseLow * 0.12) * arc * arc;
                    break;
                }
                case 2:
                    input = (carrier * 0.48 + sin(phase * 0.501) * 0.32)
                        * sin(PI * progress) * (0.65 + 0.35 * sin(tau * progress * (2 + motion * 7)));
                    break;
                case 3:
                    input = (noiseLow * 0.95 + carrier * 0.36 + sin(phase * 0.25) * 0.21) * tear;
                    break;
                case 4:
                    packet += packetStep;
                    if (packet >= 1 || i === 0) { packet %= 1; packetEnvelope = 0.45 + random() * 0.5; }
                    input = (sin(phase + floor(progress * 13) * 1.7) + noise * 0.12) * packetEnvelope * (1 - progress);
                    packetEnvelope *= packetRadius;
                    break;
                default:
                    input = (carrier * 0.9 + sin(phase * 2.071) * 0.18 + noiseLow * 0.04) * pulse;
            }
            pulse *= pulseRadius; tear *= tearRadius;
            let sum = 0;
            for (const line of lines) {
                const newReal = line.real * line.c - line.imag * line.s;
                line.imag = line.real * line.s + line.imag * line.c; line.real = newReal;
                let position = line.index - line.delay - line.depth * line.imag;
                if (position < 0) position += line.buffer.length;
                const before = floor(position), fraction = position - before;
                const after = before + 1 === line.buffer.length ? 0 : before + 1;
                const sample = line.buffer[before] * (1 - fraction) + line.buffer[after] * fraction;
                line.filter += (sample - line.filter) * damping;
                line.read = line.filter;
                sum += line.read;
            }
            // I - 2vv^T with v=(1,1,1,1)/2 conserves energy at the junction.
            for (const line of lines) {
                line.buffer[line.index] = input * 0.5 + feedback * (line.read - sum * 0.5);
                if (++line.index === line.buffer.length) line.index = 0;
            }
            let wet = sum * 0.65;
            if (dispersion > 0) {
                for (const stage of allpasses) {
                    const delayed = stage.buffer[stage.index];
                    const scattered = delayed - apGain * wet;
                    stage.buffer[stage.index] = wet + apGain * scattered;
                    if (++stage.index === stage.buffer.length) stage.index = 0;
                    wet = scattered;
                }
            }
            output[i] = (1 - field) * input + field * wet;
        }
        if (reverse > 0) {
            for (let i = 0; i < floor(count / 2); i++) {
                const opposite = count - 1 - i, a = output[i], b = output[opposite];
                output[i] = a * (1 - reverse) + b * reverse;
                output[opposite] = b * (1 - reverse) + a * reverse;
            }
        }
        const rendered = SoundDSP.finish(output, volume);
        let peak = 0;
        for (const sample of rendered) peak = max(peak, Math.abs(sample));
        // Some fields cancel much of their excitation. Restore presence with one
        // bounded gain for the whole sound, preserving every transient and tail.
        // Apply it after finish so its tanh cannot flatten the stronger waveform.
        if (peak > volume * 0.00001) {
            const gain = min(4, max(1, volume * 0.9 / peak));
            if (gain > 1) for (let i = 0; i < rendered.length; i++) rendered[i] *= gain;
        }
        return rendered;
    }
}

// js/audio/Swarmr_DSP.js
// Independent moving emitters synchronize into a flock, or scatter into a cloud.
class Swarmr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',1.8,0.25,5);
        const frames=Math.round(duration*rate), out=new Float32Array(frames);
        const count=Math.round(value('count',14,3,32)), kind=Math.round(value('kind',0,0,5));
        const speed=value('speed',0.5), cohesion=value('cohesion',0.3), agitation=value('agitation',0.25);
        const size=value('size',0.45), movement=value('movement',0.5), scatter=value('scatter',0.2);
        const random=SoundDSP.rng(value('seed',0.5)), sin=Math.sin, pow=Math.pow, min=Math.min, max=Math.max, pi=Math.PI;
        const base=90*pow(2,(1-size)*3.8), pulseRate=2+speed*17;
        const gain=0.44/Math.sqrt(count), tau=Math.PI*2;
        for(let agent=0;agent<count;agent++) {
            const start=Math.floor(random()*scatter*frames*0.42);
            const pulseOffset=random()*(1-cohesion), initialPhase=random()*tau;
            const spread=(random()-0.5)*(0.08+0.8*(1-cohesion));
            const detune=pow(2,spread), driftPhase=random()*tau;
            const driftRate=0.4+random()*2, center=0.4+random()*0.2;
            const voiceGain=gain*(0.8+random()*0.4);
            const pulseSpeed=pulseRate*(1+(random()-0.5)*(1-cohesion)*0.3);
            let phase=initialPhase, filteredNoise=0, wingNoise=0;
            for(let i=start;i<frames;i++) {
                const t=i/rate, age=(i-start)/(frames-start);
                const travel=1+movement*0.55*(1-2*age);
                const jitter=1+agitation*0.12*sin(tau*driftRate*t+driftPhase);
                const beat=(t*pulseSpeed+pulseOffset)%1;
                const wing=sin(tau*beat), positive=max(0,wing);
                // Opposite strokes have different force; an individual wing never holds a pure note.
                const stroke=pow(positive,3)+0.32*pow(max(0,-wing),5);
                let frequency=base*detune*travel*jitter, envelope=1, signal;
                if(kind===1) { frequency*=1.3+2.2*(1-beat);envelope=pow(positive,6); }
                else if(kind===2) frequency*=0.32;
                else if(kind===3) {
                    frequency*=2.3;
                    // Each arrival contributes a tick even when the shared clock's
                    // first pulse passed before this emitter entered a short sound.
                    const arrivalBeat=(i-start)*pulseSpeed/rate;
                    envelope=max(beat<0.2?pow(1-beat/0.2,5):0,
                        arrivalBeat<0.2?pow(1-arrivalBeat/0.2,5):0);
                    const paired=beat-0.24-agitation*0.035*sin(tau*driftRate*t+driftPhase);
                    if(paired>=0 && paired<0.16) envelope+=0.62*pow(1-paired/0.16,4);
                }
                else if(kind===4) frequency*=0.75;
                else if(kind===5) frequency*=0.28;
                phase+=tau*frequency/rate;
                // Keep accumulated phase small without a modulo in the oscillator loop.
                if(phase>tau)phase-=tau;
                const noise=random()*2-1;
                filteredNoise+=0.08*(noise-filteredNoise);
                wingNoise+=(noise-wingNoise)*(0.16+0.32*(1-size));
                const turbulence=wingNoise-filteredNoise;
                const airflow=1+agitation*0.4*sin(tau*(driftRate*1.73)*t+initialPhase);
                switch(kind) {
                    case 0:
                        signal=(sin(phase)+0.22*sin(phase*2)+0.12*sin(phase*3))*(0.08+0.4*stroke);
                        signal+=(turbulence*3.4+filteredNoise*0.6)*(0.12+1.4*stroke)*airflow;
                        break;
                    case 1: signal=(sin(phase)+0.2*sin(phase*2))*envelope;break;
                    case 2: {
                        // The motor turns below the blade-pass tone; narrow blade wakes carry broadband air.
                        const blade=pow(0.5+0.5*sin(phase*3),5);
                        signal=(0.62*sin(phase)+0.28*sin(phase*3)+0.15*sin(phase*6))*(0.75+0.25*wing);
                        signal+=(turbulence*2.1+noise*0.12)*(0.25+blade)*airflow;
                        break;
                    }
                    case 3: signal=(noise*0.65+sin(phase)*0.5)*envelope;break;
                    case 4: signal=sin(phase)*(0.75+0.25*wing)+0.12*sin(phase*2);break;
                    default: signal=(filteredNoise*2.5+sin(phase)*0.25+noise*0.07)*(0.7+0.3*wing);
                }
                const distance=(age-center)*3;
                const flyby=1/(1+movement*distance*distance*4);
                const window=kind===3 ? min(1,(i-start)/(rate*0.002),(frames-1-i)/(rate*0.005))
                    : pow(max(0,sin(pi*age)),0.7);
                out[i]+=signal*window*flyby*voiceGain;
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}

// js/audio/Rustlr_DSP.js
// Surface friction gathers elastic tension, then releases as slips and folds.
// Each material has its own compliance and loss; no oscillator supplies a tone.
class Rustlr_DSP {
    static materials=[
        {cutoff:4200,soft:0.35,highpass:0.65,crease:0.85,stick:0.5,flex:720},
        {cutoff:950,soft:1,highpass:0.2,crease:0.08,stick:0.15,flex:180},
        {cutoff:1900,soft:0.65,highpass:0.32,crease:0.38,stick:1,flex:330},
        {cutoff:6400,soft:0.25,highpass:0.72,crease:1.1,stick:0.6,flex:1150},
        {cutoff:12500,soft:0.06,highpass:0.92,crease:1.35,stick:0.3,flex:2600},
        {cutoff:4500,soft:0.15,highpass:0.55,crease:0.5,stick:0.2,flex:1500}
    ];

    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate, duration=value('duration',0.65,0.08,3);
        const frames=Math.round(duration*rate), out=new Float32Array(frames);
        const kind=Math.round(value('material',0,0,5)), material=this.materials[kind];
        const gesture=Math.round(value('gesture',1,0,3)), grain=value('grain',0.45), density=value('density',0.5);
        const motion=value('motion',0,-1,1), pressure=value('pressure',0.5), brightness=value('brightness',0.5);
        const folds=Math.round(value('folds',3,1,12)), random=SoundDSP.rng(value('seed',0.5));
        const sin=Math.sin, exp=Math.exp, pow=Math.pow, abs=Math.abs, min=Math.min, max=Math.max;
        const round=Math.round, floor=Math.floor, pi=Math.PI;
        const cutoff=material.cutoff*(0.22+brightness*1.18)/(1+grain*0.65)*(0.8+pressure*0.4);
        const filter=1-exp(-2*pi*cutoff/rate), slowFilter=1-exp(-2*pi*max(60,cutoff*0.13)/rate);
        const flexFilter=1-exp(-2*pi*material.flex*(0.7+pressure*0.8)/rate);
        const grainFrames=max(8,round((0.0007+grain*grain*0.023)*(1+material.soft)*rate));
        const count=max(8,round(duration*(48+density*780)/(1+grain*1.4)));
        const clusterCount=folds+2, centers=[];
        for(let i=0;i<clusterCount;i++) centers.push((i+0.2+random()*0.6)/clusterCount);
        const normalizer=1/Math.sqrt(1+count*grainFrames/frames*0.12);
        const gain=(0.24+pressure*0.76)*normalizer*2;
        const addGrain=(start,length,strength,crease)=>{
            let low=0, slow=0, flex=0, previousFlex=0;
            for(let j=0;j<length && start+j<frames;j++) {
                const noise=random()*2-1;
                low+=(noise-low)*filter;
                slow+=(low-slow)*slowFilter;
                flex+=(low-flex)*flexFilter;
                const age=j/length;
                // Compliant folds bend for longer; thin film releases abruptly.
                const attack=crease ? 0.025+material.soft*0.22 : 0.5;
                const window=crease ? min(1,age/attack)*exp(-age*(5-material.soft*2))
                    : sin(pi*age)*sin(pi*age);
                const surface=low-slow*material.highpass;
                const bending=(flex-previousFlex)*rate/(material.flex*2*pi);
                out[start+j]+=(surface+(crease?bending*(0.5+material.soft):0))*window*strength;
                previousFlex=flex;
            }
        };
        for(let i=0;i<count;i++) {
            let position;
            if(kind===5) {
                // Zip teeth follow the pull's changing speed, with small seeded defects.
                position=pow((i+0.25+random()*0.5)/count,1.35-motion*0.35);
            } else {
                const center=centers[floor(random()*clusterCount)];
                position=max(0,min(0.96,center+(random()+random()-1)*(0.035+density*0.24)));
            }
            const length=max(6,round(grainFrames*(0.45+random()*1.1)));
            const start=round(position*(frames-length));
            addGrain(max(0,start),length,gain*(0.16+random()*0.3)*(kind===5?1.4:1),false);
        }
        for(let fold=0;fold<folds;fold++) {
            const position=(fold+0.3+random()*0.45)/folds;
            const length=max(8,round((0.003+grain*0.022+material.soft*0.016)*rate*(0.65+random()*0.65)));
            const start=max(0,round(position*(frames-length)));
            addGrain(start,length,gain*(0.42+random()*0.45)*material.crease,true);
        }
        // Elastic loading and release modulate the friction, especially for leather.
        // Pressure raises the breakaway force and makes a slip last longer.
        const slipLoss=exp(-1/((0.0015+material.soft*0.017)*(0.6+pressure)*rate));
        let friction=0, frictionSlow=0, shear=0, slip=0, motionLow=0;
        let breakaway=0.7+random()*0.6;
        for(let i=0;i<frames;i++) {
            const position=i/(frames-1), arch=max(0,sin(pi*position));
            friction+=(random()*2-1-friction)*filter;
            frictionSlow+=(friction-frictionSlow)*slowFilter;
            motionLow+=(random()*2-1-motionLow)*0.0012;
            const speed=(0.3+pow(arch,0.6))*(0.7+min(0.8,abs(motionLow)*12));
            shear+=speed*(30+density*130)/rate/(0.6+pressure*material.stick*2);
            if(shear>breakaway) {
                shear-=breakaway;
                slip+=0.45+pressure*material.stick*1.5;
                breakaway=0.65+random()*0.8;
            }
            slip*=slipLoss;
            const bed=(friction-frictionSlow*material.highpass)*gain*(0.07+density*0.12)
                *(0.6+material.soft*1.3)*speed*(0.45+material.stick*slip+shear*0.35);
            let envelope;
            if(gesture===0) envelope=pow(arch,0.35)*exp(-position*4.5)*2;
            else if(gesture===1) envelope=pow(arch,0.7)*(0.55+0.45*abs(sin(pi*2*position)));
            else if(gesture===2) envelope=pow(arch,0.45);
            else envelope=pow(arch,0.5)*(0.2+0.8*abs(sin(pi*folds*position)));
            const travel=exp(motion*(position-0.5)*5-abs(motion)*1.4);
            out[i]=(out[i]+bed)*envelope*travel;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}

// js/audio/Boomr_DSP.js
// Pressure, turbulent gas, ground/shell transmission and diffuse reflections.
// Each release mechanism has its own timing and spectrum; there is no shared snap.
class Boomr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.5,0.12,5),frames=Math.round(rate*duration);
        const out=new Float32Array(frames),size=value('size',0.5),pressure=value('pressure',0.7),blast=value('blast',0.65);
        const debris=value('debris',0.35),spread=value('spread',0.5),tail=value('tail',0.45),muffle=value('muffle',0.15);
        const mechanism=Math.round(value('mechanism',0,0,7)),space=value('space',0.25);
        const random=SoundDSP.rng(value('seed',0.5)),exp=Math.exp,min=Math.min,pow=Math.pow,sin=Math.sin;
        const tau=2*Math.PI,coefficient=hz=>1-exp(-tau*hz/rate);
        const types=[
            {front:1,gas:1,body:1,decay:1,brightness:1},
            {front:0.55,gas:1.3,body:0.8,decay:1.75,brightness:0.65},
            {front:1.5,gas:0.2,body:1.6,decay:1.5,brightness:0.08},
            {front:1.1,gas:0.65,body:1.8,decay:1.45,brightness:0.4},
            {front:0.7,gas:0.65,body:1.5,decay:0.8,brightness:0.5},
            {front:0.6,gas:0.5,body:0.22,decay:0.2,brightness:1.5},
            {front:0.35,gas:1.6,body:0.3,decay:2,brightness:2.5},
            {front:0.9,gas:0.15,body:2.2,decay:0.55,brightness:0.15}
        ];
        const type=types[mechanism];
        const gas=value('gas',0.25),aftershock=value('aftershock',0.25),rubbleSize=value('rubbleSize',0.5);
        const events=[{time:mechanism===7 ? 0.08+size*0.07 : 0.007,gain:1}];
        if(mechanism===4) for(let j=0;j<5;j++) events.push({time:duration*(0.12+j*0.12)*(0.8+random()*0.3),gain:0.75-j*0.09});
        if(mechanism===2) for(let j=0;j<3;j++) events.push({time:0.06+(0.1+size*0.18)*pow(1.42,j),gain:0.44*pow(0.63,j)});
        const pressureDecay=(0.024+size*0.18)*type.decay;
        const gasDecay=(0.022+duration*(0.045+tail*0.28))*type.decay;
        const frontTime=(0.0014+size*0.01)*(mechanism===2?2.5:mechanism===5?0.45:1);
        const lowRate=coefficient(40+120*(1-size)),midRate=coefficient(200+650*(1-size));
        const dcRate=coefficient(15),motionRate=coefficient(4+10*(1-size));
        for(const event of events) {
            const start=Math.round(event.time*rate);
            let low=0,mid=0,high=0,dc=0,drift=0,wind=0,gasLow=0,gasDC=0,shellPhase=0;
            for(let i=start;i<frames;i++) {
                const t=(i-start)/rate,n=random()*2-1,n2=random()*2-1;
                low+=lowRate*(n-low);mid+=midRate*(n-mid);dc+=dcRate*(low-dc);
                drift+=motionRate*(n2-drift);
                gasLow+=lowRate*(n2-gasLow);gasDC+=dcRate*(gasLow-gasDC);
                const cooling=exp(-t/(gasDecay*0.65));
                const highRate=coefficient(140+(650+8500*pow(1-size,2))*type.brightness*cooling);
                high+=highRate*(n2-high);wind+=coefficient(85+260*cooling)*(n2-wind);
                const q=t/frontTime,front=(1-q)*exp(-q);
                const pressureBody=(low-dc)*5.5*exp(-t/pressureDecay);
                const gasAttack=mechanism===1?(1-exp(-t/(0.026+size*0.08))):1-exp(-t/0.002);
                const billow=0.8+Math.abs(drift)*6;
                const plume=((high-wind)*0.65+wind*3.2)*exp(-t/gasDecay)*gasAttack*billow;
                const rollingSource=mechanism===1?gasLow-gasDC:low-dc;
                const roll=rollingSource*4.2*exp(-t/(0.05+duration*(0.08+tail*0.25)))*(1-exp(-t/0.028));
                let transmission=0;
                if(mechanism===1) {
                    // A short hollow fuel container flexing as it opens.
                    shellPhase+=tau*(95+170*(1-size))*(1-0.14*(1-exp(-t/0.04)))/rate;
                    transmission=(sin(shellPhase)+0.23*sin(shellPhase*2.37))*exp(-t/(0.018+size*0.045))*0.2;
                } else if(mechanism===2) {
                    // Cavitation re-expansions, seeded at aperiodic spacings above.
                    transmission=(1-t/(frontTime*2))*exp(-t/(frontTime*2))*0.9;
                } else if(mechanism===3) {
                    transmission=(mid-low)*5.5*exp(-t/(0.08+size*0.2))*(1-exp(-t/0.012));
                }
                out[i]+=event.gain*(pressure*(front*type.front+pressureBody*type.body+transmission)
                    +blast*type.gas*plume+tail*type.body*roll)*0.8;
            }
        }
        // A gas jet has an audible opening and several uneven billows, rather
        // than sharing the detonation's instantaneous noise envelope.
        const gasRandom=SoundDSP.rng(value('seed',0.5)*0.71+0.193);
        const jetDelay=mechanism===6 ? 0.015 : mechanism===1 ? 0.045 : 0.07+size*0.045;
        const jetLife=(0.1+duration*(0.12+tail*0.3))*(mechanism===6?1.5:mechanism===2?0.35:mechanism===5?0.12:1);
        const gasLowRate=coefficient(50+80*(1-size));
        const gasHighRate=coefficient(mechanism===2 ? 170 : 700+4700*pow(1-size,0.65));
        let jetLow=0,jetHigh=0,jetMotion=0;
        for(let i=0;i<frames;i++) {
            const t=i/rate-jetDelay;
            const n=gasRandom()*2-1;
            jetLow+=gasLowRate*(n-jetLow);jetHigh+=gasHighRate*(n-jetHigh);
            jetMotion+=coefficient(13)*(gasRandom()*2-1-jetMotion);
            if(t>=0 && gas>0) {
                const opening=(1-exp(-t/(0.02+size*0.035)));
                const envelope=opening*exp(-t/jetLife);
                const billow=0.48+Math.abs(jetMotion)*9+0.25*pow(sin(t*(11+size*9)),2);
                out[i]+=gas*(mechanism===5?0.2:1)*envelope*billow*((jetHigh-jetLow)*1.9+jetLow*2.2);
            }
            if(mechanism===7 && t+jetDelay<events[0].time) {
                const u=(t+jetDelay)/events[0].time;
                out[i]+=(jetHigh-jetLow)*blast*pow(u,3)*0.65;
            }
        }
        // Secondary fronts travel through heavy material. Separate random streams
        // keep their placement stable when the user changes gas or debris level.
        const shockRandom=SoundDSP.rng(value('seed',0.5)*0.61+0.317);
        const shockCount=2+Math.round(aftershock*4);
        for(let event=0;event<shockCount && aftershock>0;event++) {
            const arrival=0.12+duration*(0.04+event*0.115)*(0.8+shockRandom()*0.4);
            const start=Math.round(arrival*rate),life=(0.025+size*0.1)*(0.7+shockRandom()*0.6);
            const strength=aftershock*pow(0.7,event)*(0.75+size*0.8)*(mechanism===5?0.06:1);
            let low=0,dc=0;
            const lp=coefficient(55+90*(1-size));
            for(let i=start;i<Math.min(frames,start+Math.ceil(life*8*rate));i++) {
                const t=(i-start)/rate,q=t/(0.006+size*0.016);
                low+=lp*(shockRandom()*2-1-low);dc+=coefficient(12)*(low-dc);
                out[i]+=strength*((1-q)*exp(-q)*0.8+(low-dc)*7*(1-exp(-t/0.009))*exp(-t/life));
            }
        }
        const pieces=Math.round(debris*48);
        for(let piece=0;piece<pieces;piece++) {
            const start=Math.floor((0.018+rubbleSize*0.055+random()*duration*(0.04+spread*0.8))*rate);
            const chunk=random(),life=(0.002+chunk*0.025)*(0.25+rubbleSize*2.5),gain=debris*(0.1+random()*0.3)*(0.7+rubbleSize);
            const length=min(frames-start,Math.ceil(life*rate*7)),damping=exp(-1/(life*rate));
            const dustRate=coefficient((1200+random()*8500)*pow(1-rubbleSize*0.94,2)),bodyRate=coefficient(45+random()*600*pow(1-rubbleSize*0.85,2));
            let dust=0,body=0,envelope=1;
            for(let j=0;j<length;j++) {
                const noise=random()*2-1;
                dust+=dustRate*(noise-dust);body+=bodyRate*(noise-body);
                const q=(j/rate)/(0.0004+rubbleSize*0.009);
                out[start+j]+=(dust*(1-rubbleSize*0.7)+body*(0.5+rubbleSize*5)+(1-q)*exp(-q)*rubbleSize)*envelope*gain;envelope*=damping;
            }
        }
        if(space>0) {
            // Three unequal, damped recirculating paths smear the pressure field.
            const delays=[0.071,0.113,0.173].map(t=>new Float32Array(Math.max(1,Math.round(t*(0.6+space*1.8)*rate))));
            const heads=[0,0,0],smoothed=[0,0,0];
            for(let i=0;i<frames;i++) {
                const input=out[i];let echo=0;
                for(let j=0;j<3;j++) {
                    const buffer=delays[j],head=heads[j],sample=buffer[head];
                    smoothed[j]+=0.08*(sample-smoothed[j]);
                    buffer[head]=input*0.36+smoothed[j]*(0.2+space*0.48);
                    echo+=smoothed[j];heads[j]=(head+1)%buffer.length;
                }
                out[i]+=echo*space*0.7;
            }
        }
        const finalRate=coefficient(80+15000*pow(1-muffle,3));
        let filtered=0;
        for(let i=0;i<frames;i++){filtered+=finalRate*(out[i]-filtered);out[i]=filtered;}
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}

// js/audio/Zappr_DSP.js
// Seeded leader arcs split into shorter branches over an unstable mains field.
class Zappr_DSP {
    static render(p) {
        const value=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.2,0.12,5),frames=Math.round(duration*rate),out=new Float32Array(frames);
        const arcs=Math.round(value('arcs',7,1,24)),voltage=value('voltage',0.55),branching=value('branching',0.4);
        const crackle=value('crackle',0.45),hum=value('hum',0.2),spark=value('spark',0.65),spread=value('spread',0.7),decay=value('decay',0.4);
        const random=SoundDSP.rng(value('seed',0.5)),sin=Math.sin,exp=Math.exp,pow=Math.pow,min=Math.min,max=Math.max;
        const tau=2*Math.PI,humFrequency=42+voltage*65,events=[];
        for(let arc=0;arc<arcs;arc++) {
            const position=arc===0?0.004:(arc+random()*0.65)/arcs*duration*(0.03+spread*0.86);
            const life=0.008+decay*0.1,frequency=400+voltage*4800*(0.6+random()*0.8);
            events.push([position,life,frequency,0.55+random()*0.4]);
            const branches=Math.round(branching*(2+random()*5));
            for(let branch=0;branch<branches;branch++)events.push([position+life*(0.3+random()*2),life*(0.18+random()*0.55),frequency*(0.5+random()*1.2),branching*(0.15+random()*0.25)]);
        }
        let phase=0,crackleEnv=0,noiseLow=0;
        const crackleFall=exp(-1/(rate*(0.001+decay*0.014)));
        for(let i=0;i<frames;i++) {
            const t=i/rate,noise=random()*2-1;noiseLow+=0.075*(noise-noiseLow);
            phase+=tau*humFrequency/rate;if(phase>tau)phase-=tau;
            if(random()<crackle*(12+voltage*130)/rate)crackleEnv=0.15+random()*0.55;
            crackleEnv*=crackleFall;
            const field=hum*(sin(phase)+0.28*sin(phase*3)+0.15*sin(phase*7))*0.27;
            out[i]=(field+crackleEnv*(noise-noiseLow)*crackle)*min(1,t/0.006)*pow(max(0,1-t/duration),0.2+decay*0.6);
        }
        for(const [time,life,frequency,gain] of events) {
            const start=Math.round(time*rate),length=min(frames-start,Math.ceil(life*rate*6));
            let phase=random()*tau,low=0;
            for(let j=0;j<length;j++) {
                const age=j/rate,noise=random()*2-1;
                phase+=tau*frequency*(0.3+0.7*exp(-age/life))/rate;if(phase>tau)phase-=tau;
                low+=0.2*(noise-low);
                const discharge=(0.4+spark*0.5)*(noise-low)+sin(phase+sin(phase*0.47)*voltage*2)*(1-spark*0.65);
                const restrike=0.65+0.35*max(0,sin(tau*age*(75+voltage*290)));
                out[start+j]+=discharge*gain*exp(-age/life)*restrike*min(1,j/12);
            }
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}

// js/audio/Whooshr_DSP.js
// A moving air source: turbulent bands and a tonal edge sweep past the listener.
class Whooshr_DSP {
    static render(p) {
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?SoundDSP.clamp(p[name],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=value('duration',0.6,0.1,5),length=Math.round(rate*duration);
        const out=new Float32Array(length),random=SoundDSP.rng(value('seed',0.5));
        const size=value('size',0.4),air=value('air',0.8),whistle=value('whistle',0.25);
        const movement=value('movement',0.7),focus=value('focus',0.6),flutter=value('flutter',0.1);
        const sin=Math.sin,pow=Math.pow,exp=Math.exp,min=Math.min,pi=Math.PI,tau=2*pi;
        const base=190*pow(2,(1-size)*3.1),offset=random()*tau,beat=8+random()*10;
        let low=0,broad=0,phase=offset;
        for(let i=0;i<length;i++) {
            const u=i/(length-1),t=i/rate,position=(u-0.5)*2;
            const approach=1-movement*0.7*position;
            const envelope=pow(sin(pi*u),0.6+focus*5)/(1+focus*position*position*7);
            const gust=1-flutter*0.65+flutter*0.65*sin(tau*beat*t+offset)*sin(tau*beat*t+offset);
            const cutoff=min(12000,(350+5500*(1-size))*approach);
            const noise=random()*2-1;
            low+=(1-exp(-tau*cutoff/rate))*(noise-low);
            broad+=(1-exp(-tau*cutoff*0.14/rate))*(noise-broad);
            phase+=tau*base*approach*(1+flutter*0.025*sin(tau*beat*t))/rate;
            if(phase>tau)phase-=tau;
            out[i]=((low-broad)*air*2.7+(sin(phase)+0.12*sin(phase*2))*whistle*0.45)*envelope*gust;
        }
        return SoundDSP.finish(out,value('masterVolume',0.5));
    }
}

// js/audio/Bouncr_DSP.js
// Coupled object and surface modes are excited by the same finite contact pulse.
class Bouncr_DSP {
    static render(p) {
        const v=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const {sin,exp,pow,min,max,sqrt,round,PI}=Math,tau=PI*2,rate=SoundDSP.rate;
        const duration=v('duration',2,0.2,5),out=new Float32Array(round(rate*duration));
        const random=SoundDSP.rng(v('seed',0.5)),material=round(v('material',0,0,4)),surface=round(v('surface',0,0,5));
        const count=round(v('count',1,1,20)),bounce=v('bounce',0.65),gravity=v('gravity',0.5);
        const size=v('size',0.5),hardness=v('hardness',0.6),spin=v('spin',0),force=v('force',0.65),tail=v('tail',0.4);
        // Frequency, decay, stiffness and inharmonic partials describe each body.
        const objects=[
            {pitch:0.55,decay:0.041,hard:0.22,ratios:[1,1.97,3.17,4.8]},
            {pitch:1,decay:0.030,hard:0.64,ratios:[1,2.43,4.13,6.27]},
            {pitch:2.5,decay:0.16,hard:1,ratios:[1,1.47,2.71,4.09]},
            {pitch:3.3,decay:0.10,hard:0.95,ratios:[1,2.76,5.4,8.13]},
            {pitch:0.72,decay:0.025,hard:0.86,ratios:[1,1.91,3.47,5.31]}
        ];
        const surfaces=[
            {pitch:260,decay:0.022,hard:0.95,ring:0.30,ratios:[1,1.61,2.83,4.41]},
            {pitch:135,decay:0.075,hard:0.6,ring:0.72,ratios:[1,2.18,3.72,5.41]},
            {pitch:330,decay:0.26,hard:0.93,ring:0.85,ratios:[1,1.59,2.32,3.79]},
            {pitch:710,decay:0.18,hard:1,ring:0.70,ratios:[1,1.71,3.04,4.93]},
            {pitch:78,decay:0.017,hard:0.16,ring:0.18,ratios:[1,1.83,2.81,4.18]},
            {pitch:90,decay:0.016,hard:0.035,ring:0.15,ratios:[1,2.11,3.43,4.72]}
        ];
        const object=objects[material],target=surfaces[surface];
        const stiffness=sqrt(object.hard*target.hard)*(0.18+hardness*0.82);
        const transfer=0.15+target.hard*0.85,decayScale=(0.3+tail*2.7)*(0.75+force*0.5);
        const base=(95+790*pow(1-size,2))*object.pitch;
        let time=0.012,gap=min(duration*0.42,0.18+0.45*(1-gravity));
        for(let hit=0;hit<count;hit++) {
            const start=round(time*rate);if(start>=out.length)break;
            const strength=(0.18+force*0.82)*pow(0.53+bounce*0.43,hit)*(0.94+random()*0.06);
            const contact=(0.0008+(1-stiffness)*0.013)/(0.65+force*0.8);
            const objectDecay=object.decay*decayScale*(0.3+transfer*0.7)*(0.75+bounce*0.35);
            const surfaceDecay=target.decay*decayScale*(0.8+size*0.5);
            const detune=1+(random()-0.5)*(0.025+spin*0.07);
            const modes=[];
            for(let mode=0;mode<4;mode++) {
                modes.push({frequency:min(rate*0.42,base*object.ratios[mode]*detune),phase:0,
                    decay:objectDecay/(1+mode*(0.2+(1-hardness)*0.4)),gain:transfer*0.72*pow(stiffness+0.18,mode*0.48)/(1+mode*0.8)});
                modes.push({frequency:min(rate*0.42,target.pitch*(1.6-size)*target.ratios[mode]*(0.97+random()*0.06)),phase:0,
                    decay:surfaceDecay/(1+mode*0.48),gain:target.ring*0.72*pow(stiffness+0.12,mode*0.6)/(1+mode)});
            }
            // A broad soft contact cannot excite modes faster than its pressure pulse.
            for(const mode of modes)mode.gain/=1+pow(mode.frequency*contact*0.4,2);
            const end=min(out.length,start+Math.ceil(max(contact*10,max(objectDecay,surfaceDecay)*7)*rate));
            let low=0,rub=0,absorbed=0;
            const tone=1-exp(-tau*(100+stiffness*11000)/rate);
            const absorption=1-exp(-tau*(100+pow(target.hard,2)*14000)/rate);
            for(let i=start;i<end;i++) {
                const t=(i-start)/rate,attack=min(1,t/(0.00025+contact*0.3));
                const noise=random()*2-1;low+=(noise-low)*tone;rub+=(noise-rub)*0.08;
                let body=0;
                for(const mode of modes) {
                    // Integrating instantaneous frequency gives a smooth compressed-rubber release.
                    const bend=material===0?1+(0.2+force*0.65)*exp(-t/(contact*2.5)):1;
                    mode.phase+=tau*mode.frequency*bend/rate;
                    body+=sin(mode.phase)*mode.gain*exp(-t/mode.decay);
                }
                const contactNoise=low*(0.18+stiffness*0.6)*exp(-t/contact);
                const scatter=(surface===4?0.6:surface===0?0.16:0.04)*low*exp(-t/(0.014+tail*0.035));
                const scrape=rub*spin*0.6*exp(-t/(0.025+spin*0.08))*(0.65+0.35*sin(tau*(110+random()*30)*t));
                absorbed+=(body+contactNoise+scatter+scrape-absorbed)*absorption;
                out[i]+=absorbed*strength*attack;
            }
            time+=gap;gap=max(0.006,gap*(0.4+bounce*0.54)*(1-spin*0.12));
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}

// js/audio/Breathr_DSP.js
// Turbulent air changes colour with direction; obstructed airways flutter into a snore.
class Breathr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,tau=PI*2,duration=value('duration',2.7,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        // Missing mode retains the original cycle for saved/raw parameter objects.
        const single=round(value('mode',1,0,1))===0,inward=(1-value('direction',1,-1,1))/2;
        const random=SoundDSP.rng(value('seed',0.5)),cycles=single?1:round(value('cycles',1,1,10)),source=round(value('source',0,0,2));
        const effort=value('effort',0.55),inhale=value('inhale',0.42,0.1,0.9),hold=value('hold',0.04,0,0.7);
        const throat=value('throat',0.5),rasp=value('rasp',0.1),flutter=value('flutter',0.15),space=value('space',0.1);
        const slot=out.length/cycles,inEnd=(1-hold)*inhale*0.9,outStart=inEnd+hold*0.9+0.025,outEnd=0.965;
        const delay=round(rate*(0.022+space*0.075)),gain=1.5+effort*1.5;
        const variations=Array.from({length:cycles},()=>0.88+random()*0.24);
        const radius=exp(-PI*550/rate),r2=radius*radius,bandGain=(1-radius)*1.6;
        let low=0,highpass=0,y1=0,y2=0,previous=0,previous2=0,wander=0,phase=random()*tau;
        let coefficient=0,cutoff=0,heldNoise=0;
        for(let i=0;i<out.length;i++) {
            const position=(i%slot)/slot,cycle=min(cycles-1,floor(i/slot));
            const inhaling=position<inEnd,exhaling=position>outStart&&position<outEnd;
            const blend=single?inward:inhaling?1:0;
            const local=single?i/max(1,out.length-1):inhaling?position/inEnd:exhaling?(position-outStart)/(outEnd-outStart):0;
            const arch=pow(max(0,sin(PI*local)),single?0.7+0.1*blend:inhaling?0.8:0.7);
            const shape=single?(1-0.36*local)*(1-blend)+(0.8+0.2*local)*blend:inhaling?0.8+0.2*local:1-0.36*local;
            const airflow=arch*shape*variations[cycle];
            const noise=random()*2-1;
            wander+=(noise-wander)*0.0025;
            if(source===1&&i%round(5+throat*22)===0)heldNoise=noise>0?0.8:-0.8;
            const excitation=source===1?heldNoise:noise;
            if((i&31)===0) {
                // Inhale jets are brighter; the mouth and chest soften the released air.
                const airHz=single?(750+effort*1600)*(1-blend)+(2400+effort*2700)*blend:inhaling?2400+effort*2700:750+effort*1600;
                const hz=airHz*(1-throat*0.38)*(0.75+airflow*0.25);
                cutoff=1-exp(-tau*hz/rate);
                coefficient=2*radius*cos(tau*(single?510+490*blend:inhaling?1000:510)*(1.35-throat*0.6)/rate);
            }
            low+=(excitation-low)*cutoff;
            highpass+=(low-highpass)*(1-exp(-tau*(single?110+120*blend:inhaling?230:110)/rate));
            const turbulent=low-highpass;
            const resonant=bandGain*(turbulent-previous2)+coefficient*y1-r2*y2;
            y2=y1;y1=resonant;previous2=previous;previous=turbulent;
            phase+=tau*(24+(1-throat)*44)*(1+flutter*0.3*sin(tau*2.3*i/rate)+wander*0.9)/rate;
            const obstruction=source===2?0.72+rasp*0.27:rasp*0.22;
            const flap=pow(max(0,sin(phase)),3);
            const airway=1-obstruction+obstruction*flap;
            const tremor=max(0.2,1+wander*flutter*6+flutter*0.07*sin(tau*7.3*i/rate));
            let envelope=airflow*tremor;
            if(source===1)envelope=round(envelope*12)/12;
            // Snore pressure pulses are driven by turbulent flow, not a sustained vocal note.
            const tissue=source===2?(flap-0.212)*rasp*0.3*arch:0;
            out[i]=((turbulent*0.85+resonant*0.8)*airway+tissue)*envelope*gain;
            if(i>=delay)out[i]+=out[i-delay]*space*0.38;
        }
        return SoundDSP.finish(out,volume);
    }
}

// js/audio/Choirr_DSP.js
// Independent band-limited vocal sources excite three vowel formants per singer.
class Choirr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,tau=PI*2,duration=value('duration',2.5,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),voices=round(value('voices',6,1,12));
        const pitch=55*pow(2,value('pitch',0.5)*4),vowel=value('vowel',0.35);
        const detune=value('detune',0.4),swell=value('swell',0.5),breath=value('breath',0.1),motion=value('motion',0.4);
        const harmony=round(value('harmony',1,0,4));
        const chords=[[0],[0,4,7,12],[0,3,7,12],[0,7,12,19],[0,1,6,10]];
        const vowels=[[350,800,2300],[750,1150,2600],[300,2200,3100]];
        const vIndex=vowel<0.5?0:1,blend=vowel<0.5?vowel*2:(vowel-0.5)*2;
        const gain=1.9/Math.sqrt(voices),radii=[exp(-PI*85/rate),exp(-PI*120/rate),exp(-PI*190/rate)];
        for(let voice=0;voice<voices;voice++) {
            const note=chords[harmony][voice%chords[harmony].length];
            const frequency=pitch*pow(2,note/12+(random()-0.5)*detune*0.08);
            const formantScale=0.92+random()*0.16;
            const coeff=radii.map((r,k)=>2*r*cos(tau*(vowels[vIndex][k]*(1-blend)+vowels[vIndex+1][k]*blend)*formantScale/rate));
            const y1=[0,0,0],y2=[0,0,0],squares=radii.map(r=>r*r),gains=radii.map(r=>1-r);
            const initial=random()*tau,vibratoRate=4.2+random()*1.8;
            const onset=round(random()*motion*min(out.length*0.1,3000));
            let phase=random(),previous=0,previous2=0;
            for(let i=onset;i<out.length;i++) {
                const age=(i-onset)/(out.length-onset),t=i/rate;
                const step=frequency*(1+motion*0.009*sin(tau*vibratoRate*t+initial))/rate;
                phase+=step;if(phase>=1)phase-=1;
                let source=2*phase-1;
                // PolyBLEP softens the discontinuity before the throat filters.
                if(phase<step){const x=phase/step;source-=x+x-x*x-1;}
                else if(phase>1-step){const x=(phase-1)/step;source-=x*x+x+x+1;}
                source=source*(1-breath*0.7)+(random()*2-1)*breath*0.35;
                let resonant=0;
                for(let band=0;band<3;band++) {
                    const sample=gains[band]*(source-previous2)+coeff[band]*y1[band]-squares[band]*y2[band];
                    y2[band]=y1[band];y1[band]=sample;
                    resonant+=sample*(band===0?1.2:band===1?0.8:0.5);
                }
                previous2=previous;previous=source;
                const envelope=pow(max(0,sin(PI*age)),0.25+swell*2.7);
                out[i]+=(resonant+sin(tau*phase)*0.065)*envelope*gain*(0.9+motion*0.1*sin(tau*0.7*t+initial));
            }
        }
        return SoundDSP.finish(out,volume);
    }
}

// js/audio/Pluckr_DSP.js
// Material-dependent waveguide strings share a damped bridge and shaped pluck.
class Pluckr_DSP {
    static render(p) {
        const {sin,atan2,exp,pow,round,floor,min,max,PI}=Math;
        const value=(name,fallback,lo=0,hi=1)=>Number.isFinite(p[name])?min(hi,max(lo,p[name])):fallback;
        const rate=SoundDSP.rate,duration=value('duration',1.8,0.15,5);
        const out=new Float32Array(round(duration*rate)),volume=value('masterVolume',0.5);
        if(volume===0)return SoundDSP.finish(out,0);
        const random=SoundDSP.rng(value('seed',0.5)),count=round(value('strings',3,1,8)),material=round(value('material',0,0,5));
        const pitch=55*pow(2,value('pitch',0.5)*4),damping=value('damping',0.25),brightness=value('brightness',0.6);
        const coupling=value('coupling',0.15),strum=value('strum',0.2),pluck=value('pluck',0.3),inharmonic=value('inharmonic',0.05);
        const tremolo=value('tremolo',0),vibrato=value('vibrato',0),speed=value('tremoloRate',4,0.2,12);
        // Flexible fibres lose high frequencies; rigid filaments disperse travelling waves.
        const matter=[
            {life:1,average:0.5,filter:0.18,bright:0.8,excite:1,dispersion:0,stages:0},
            {life:1.45,average:0.14,filter:0.65,bright:0.35,excite:1.5,dispersion:0.2,stages:1},
            {life:0.62,average:0.55,filter:0.12,bright:0.5,excite:0.6,dispersion:0.6,stages:1},
            {life:0.075,average:0.65,filter:0.1,bright:0.28,excite:0.35,dispersion:0.4,stages:1},
            {life:1.3,average:0.06,filter:0.85,bright:0.15,excite:1.8,dispersion:-0.72,stages:2},
            {life:0.95,average:0.25,filter:0.4,bright:0.5,excite:1.1,dispersion:-0.45,stages:2}
        ][material];
        const notes=[0,7,12,16,19,24,28,31],strings=[],gain=0.65/Math.sqrt(count);
        for(let s=0;s<count;s++) {
            const frequency=pitch*pow(2,notes[s]/12+(random()-0.5)*inharmonic*0.07);
            const period=rate/frequency,omega=2*PI/period,a=matter.dispersion;
            const dispersionDelay=matter.stages*2*atan2((1-a)*sin(omega/2),(1+a)*Math.cos(omega/2))/omega;
            const desired=max(2,period-matter.average-dispersionDelay),delay=max(2,floor(desired));
            const buffer=new Float32Array(delay);let low=0,mean=0;
            const location=0.05+pluck*0.9;
            for(let i=0;i<delay;i++) {
                low+=(random()*2-1-low)*min(1,(0.05+brightness*0.9)*matter.excite);
                const x=i/delay,triangle=x<location?x/location:(1-x)/(1-location);
                buffer[i]=low*0.75+(triangle-0.5)*(1-brightness)*0.75;mean+=buffer[i];
            }
            mean/=delay;for(let i=0;i<delay;i++)buffer[i]-=mean;
            strings.push({buffer,index:0,previous:0,low:0,allpass:0,allpassInput:0,
                waveInputs:new Float32Array(matter.stages),waveOutputs:new Float32Array(matter.stages),
                // Clamp the physical loop before deriving its fractional-delay coefficient.
                fraction:(1-(desired-delay))/(1+(desired-delay)),
                feedback:exp(-3/(frequency*(0.07+pow(1-damping,2)*4)*matter.life)),
                start:round(s*strum*min(rate*0.11,out.length/max(1,count)*0.65))});
        }
        let bridge=0;
        for(let i=0;i<out.length;i++) {
            let sum=0,bridgeNext=0;
            const dispersion=matter.dispersion+(material===5?0.22*sin(2*PI*1.7*i/rate):0);
            for(let s=0;s<count;s++) {
                const string=strings[s];if(i<string.start)continue;
                const current=string.buffer[string.index];
                const averaged=current*(1-matter.average)+string.previous*matter.average;string.previous=current;
                string.low+=(averaged-string.low)*(matter.filter+brightness*matter.bright);
                const input=string.low;
                let dispersed=string.fraction*input+string.allpassInput-string.fraction*string.allpass;
                string.allpassInput=input;string.allpass=dispersed;
                for(let stage=0;stage<matter.stages;stage++) {
                    const next=dispersion*dispersed+string.waveInputs[stage]-dispersion*string.waveOutputs[stage];
                    string.waveInputs[stage]=dispersed;string.waveOutputs[stage]=next;dispersed=next;
                }
                string.buffer[string.index]=string.feedback*(dispersed*(1-coupling*0.025)+bridge*coupling*0.025);
                string.index++;if(string.index===string.buffer.length)string.index=0;
                sum+=current;bridgeNext+=current;
            }
            bridge=bridgeNext/count;
            // Preserve the exact legacy render when pitch motion is disabled.
            out[i]=sum*gain*(vibrato>0?1:1-tremolo*(0.5-0.5*Math.cos(2*PI*speed*i/rate)));
        }
        // A smooth varying delay bends pitch without changing the string's decay or material.
        // Keep tremolo after this stage so its depth always means volume alone.
        if(vibrato>0){
            const dry=out.slice(),depth=(pow(2,vibrato*0.75/12)-1)*rate/(2*PI*speed);
            for(let i=0;i<out.length;i++){
                const motion=0.5-0.5*Math.cos(2*PI*speed*i/rate);
                const position=max(0,i-depth*2*motion),index=floor(position),fraction=position-index;
                out[i]=(dry[index]*(1-fraction)+dry[min(index+1,dry.length-1)]*fraction)*(1-tremolo*motion);
            }
        }
        return SoundDSP.finish(out,volume);
    }
}

// js/audio/Glitchr_DSP.js
// Captured plucks and transients are damaged by independent read/coding failures.
class Glitchr_DSP {
    static render(p) {
        const {sin,cos,exp,pow,round,floor,abs,max,min,PI}=Math,tau=PI*2;
        const v=(key,fallback,lo=0,hi=1)=>Number.isFinite(p[key])?SoundDSP.clamp(p[key],lo,hi):fallback;
        const rate=SoundDSP.rate,duration=v('duration',0.7,0.08,4),out=new Float32Array(round(duration*rate));
        const random=SoundDSP.rng(v('seed',0.5)),mode=round(v('mode',0,0,7));
        const base=80*pow(2,v('pitch',0.5)*4),fragment=v('fragment',0.3),repeat=v('repeat',0.4);
        const chaos=v('chaos',0.5),dropout=v('dropout',0.2),crush=v('crush',0.3),rateLoss=v('rate',0.3);
        const chunk=max(80,round((0.009+fragment*0.18)*rate));
        const hold=1+round(rateLoss*27),steps=pow(2,13-round(crush*11));
        // A short, evolving source gives repeated buffers recognisable attacks and timbre.
        const source=new Float32Array(round(rate*0.83)),notes=[1,1.25,0.75,1.5,1.125];
        let sourceLow=0;
        for(let i=0;i<source.length;i++) {
            const t=i/rate,note=floor(t/0.137),local=t-note*0.137,f=base*notes[note%notes.length];
            const noise=random()*2-1;sourceLow+=(noise-sourceLow)*0.12;
            const pluck=(sin(tau*f*local)+0.35*sin(tau*f*2.01*local)+0.18*sin(tau*f*3.97*local))*exp(-local*18);
            const transient=(noise-sourceLow)*exp(-local*120)*0.25;
            source[i]=(pluck*0.55+transient+sourceLow*0.24)*min(1,local/0.001);
        }
        const read=position=>{
            const wrapped=((position%source.length)+source.length)%source.length;
            const index=floor(wrapped),mix=wrapped-index;
            return source[index]*(1-mix)+source[(index+1)%source.length]*mix;
        };
        let head=0,anchor=0,speed=1,skip=false,sample=0,previous=0,dc=0,scrubLow=0;
        let dataPhase=0,dataBit=0,dataCount=0,shift=1+floor(random()*65534);
        let bandLow=0,bandMid=0,bandHigh=0,packetGain=[1,1,1,1];
        const grains=[],frozen=Array.from({length:6},(_,n)=>({phase:random()*tau,frequency:base*(1+n*0.51),gain:0}));
        let grainCountdown=0,grainOrigin=0;
        for(let i=0;i<out.length;i++) {
            const t=i/rate,j=i%chunk;
            if(j===0) {
                const fresh=i===0||random()>repeat;
                skip=i>0&&random()<dropout*0.86;
                if(fresh) {
                    anchor=floor(random()*(source.length-chunk));
                    speed=pow(2,(random()-0.5)*chaos*2.4);
                    grainOrigin=anchor;
                }
                if(mode===0||mode===6)head=anchor;
                if(mode===2) {
                    if(fresh)head=anchor;
                    speed=(random()<0.55?-1:1)*(0.2+random()*2.8)*(0.4+chaos);
                }
                packetGain=packetGain.map(()=>0.25+random()*1.2);
                if(mode===7&&fresh) {
                    for(const partial of frozen) {
                        partial.frequency=min(9000,base*(0.5+round(random()*11)/4));
                        let real=0,imaginary=0;
                        for(let k=0;k<256;k++) {
                            const captured=read(anchor+k),phase=tau*partial.frequency*k/rate;
                            real+=captured*cos(phase);imaginary+=captured*sin(phase);
                        }
                        partial.gain=0.025+min(0.22,Math.hypot(real,imaginary)/128);
                    }
                }
            }
            let value=0;
            if(mode===0) {
                // The device replays a stalled buffer until a fresh packet arrives.
                value=read(head);head+=speed;
                if(head>=anchor+chunk)head=anchor;
                value*=min(1,j/16,(chunk-j)/16);
            } else if(mode===1) {
                // Crude subband coding: independent bands have damaged packet gains and precision.
                const captured=read(head);head+=speed*(1+chaos*0.45*sin(tau*(8+fragment*25)*t));
                bandLow+=(captured-bandLow)*0.018;bandMid+=(captured-bandMid)*0.11;bandHigh+=(captured-bandHigh)*0.43;
                const bands=[bandLow,bandMid-bandLow,bandHigh-bandMid,captured-bandHigh];
                for(let band=0;band<4;band++) {
                    const resolution=pow(2,3+band-(crush*2));
                    const coded=round(bands[band]*resolution)/resolution;
                    value+=coded*packetGain[band]*(0.7+0.3*sin(tau*(11+band*7+chaos*13)*t+band));
                }
                value=value*1.7+sin(tau*base*1.43*t)*abs(bandMid-bandLow)*chaos*0.6;
            } else if(mode===2) {
                // Continuous reversible read-head motion; interpolation preserves tape-like bends.
                head+=speed*(1+chaos*0.8*sin(tau*(1.5+fragment*5)*t));
                const captured=read(head);scrubLow+=(captured-scrubLow)*min(0.95,0.07+abs(speed)*0.19);
                value=scrubLow*1.5+(random()*2-1)*0.018*chaos;
            } else if(mode===3) {
                const decimation=2+round(rateLoss*95+crush*25*(i/out.length));
                if(i%decimation===0) {
                    const levels=pow(2,8-round(crush*6)),captured=read(head);
                    let word=round((captured+1)*levels);
                    if(random()<chaos*0.22)word^=1<<floor(random()*max(1,round(crush*7)));
                    previous=word/levels-1;
                }
                head+=0.65+speed*0.45;value=previous*0.85;
            } else if(mode===4) {
                // A deterministic shift register transmits binary FSK and leaking logic edges.
                const baud=round(rate/(100+fragment*1700));
                if(dataCount--<=0) {
                    shift=((shift>>>1)^(-(shift&1)&0xB400))&65535;
                    dataBit=shift&1;dataCount=baud;
                }
                dataPhase+=tau*min(rate*0.42,base*(dataBit?7.3+chaos:4.17))/rate;
                const carrier=sin(dataPhase);
                value=(carrier>0?1:-1)*0.30+carrier*0.22+(dataBit*2-1)*0.08;
            } else if(mode===5) {
                // Several independent windowed grains overlap, with jumps and reverse fragments.
                if(grainCountdown--<=0) {
                    const length=max(100,round(chunk*(0.6+random()*0.9)));
                    grains.push({age:0,length,head:grainOrigin+(random()-0.5)*source.length*chaos,
                        speed:pow(2,(random()-0.5)*chaos*3)*(random()<chaos*0.5?-1:1)});
                    grainCountdown=max(30,round(length/(2.5+repeat*2)));
                }
                for(let n=grains.length-1;n>=0;n--) {
                    const grain=grains[n],window=0.5-0.5*cos(tau*grain.age/grain.length);
                    value+=read(grain.head)*window*0.8;grain.head+=grain.speed;
                    if(++grain.age>=grain.length)grains.splice(n,1);
                }
            } else if(mode===6) {
                // Retrigger a complete captured phrase inside a longer packet.
                const phrase=max(55,round(chunk/(1+round(repeat*5)))),position=j%phrase;
                value=read(anchor+position*(0.65+speed*0.35))*min(1,position/12,(phrase-position)/12);
                value*=0.6+0.4*exp(-position/(phrase*0.25));
            } else {
                // Retain the measured partial levels while their phases continue across packets.
                for(const partial of frozen) {
                    partial.phase+=tau*partial.frequency*(1+chaos*0.012*sin(tau*3*t))/rate;
                    value+=sin(partial.phase)*partial.gain;
                }
            }
            if(i%hold===0)sample=round(value*steps)/steps;
            // A short DC blocker prevents flipped sign bits and data pulses shifting the baseline.
            dc+=(sample-dc)*0.001;
            out[i]=skip?0:(sample-dc)*0.85;
        }
        return SoundDSP.finish(out,v('masterVolume',0.5));
    }
}

// js/synths/SynthBase.js
class SynthBase {

    sound = null;
    params = {};
    locked_params = null;

    default_params() {
        var result = {};
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            //if object, then it's a buttonselect
            if (param.constructor === Array) {
                var param_name = param[2];
                var param_default_value = param[3];
                result[param_name] = param_default_value;
            } else {
                switch (param.type) {
                    case "TEXT":
                    case "BUTTONSELECT":
                        result[param.name] = param.default_value;
                        break;
                    case "KNOB_TRANSITION":
                        result[param.name] = {start: param.default_value_l, end: param.default_value_r, curve: param.default_tween};
                        break;
                    default:
                        console.error("Unknown param type: " + param.type);
                }
            }
        }
        return result;
    };

    create_random_template() {
        this.reset_params();
        var random_template_idx = Math.floor(Math.random() * this.templates.length);
        var template = this.templates[random_template_idx];
        var template_name = template[0];
        var template_generator_name = template[2];
        var template_file_name = template[3];
        this[template_generator_name]();
        return [template_file_name, this.params];
    }


    apply_params(other_params,check_locked = false) {
        for (var key in other_params) {
            if ( !check_locked || !this.locked_param(key) ) {
                const info = this.param_info.find(p => p.name === key && p.type === "KNOB_TRANSITION");
                if (info) {
                    this.set_param(key, other_params[key]);
                } else {
                    this.params[key] = other_params[key];
                }
            }
        }
        this.sound_params = null;
    }

    param_is_disabled(param_name){
        return false;
    }

    reset_params(check_locked = false) {
        var default_params = this.default_params();
        this.apply_params(default_params,check_locked);
    }

    post_initialize(){
        this.params = this.default_params();
        this.create_locked_params_array();
        this.load_bcol_tempaltes();
    }

    load_bcol_tempaltes(){
        if (!TEMPLATES_JSON.hasOwnProperty(this.name)){
            return;
        }
        var templates_for_me = TEMPLATES_JSON[this.name];
        var template_names = Object.keys(templates_for_me);
        for (var i = 0; i < template_names.length; i++) {

            var template_name = template_names[i];
            var template_method_name = "generate_"+template_names[i];
            var template_bounds_dictionary = templates_for_me[template_name];
            this[template_method_name] = this.generate_template_function_from_bounds_dictionary(template_bounds_dictionary);
        }
    }

    create_locked_params_array() {
        if (this.locked_params) {
            return;
        }
        this.locked_params = {};
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.get_param_normalized(this.param_info[i]);
            this.locked_params[param.name] = false;
        }
        for (var i = 0; i < this.permalocked.length; i++) {
            this.locked_params[this.permalocked[i]] = true;
        }
    }

    /*********************/
    /* PARAM FUNCTIONS  */
    /*********************/

    /* returns a param with nice fields name/min/max */
    get_param_normalized(param){
        var result={};
        //if array
        if (param.constructor === Array) {
            result.name = param[2];
            result.default_value = param[3];
            result.min_value = param[4];
            result.max_value = param[5];
            result.type = "RANGE";
        } else {
            switch (param.type) {
                case "TEXT":
                    result.name = param.name;
                    result.default_value = param.default_value;
                    result.type = "TEXT";
                    break;
                case "BUTTONSELECT":
                    result.name = param.name;
                    result.default_value = param.default_value;
                    result.min_value = 0;
                    result.max_value = param.values.length;
                    result.type = "BUTTONSELECT";
                    break;
                case "KNOB_TRANSITION":
                    result.name = param.name;
                    result.default_value = {start: param.default_value_l, end: param.default_value_r, curve: param.default_tween};
                    result.min_value = param.min;
                    result.max_value = param.max;
                    result.type = "KNOB_TRANSITION";
                    break;
                default:
                    console.error("Don't know how to uniformize param type: " + param.type);
            }
        }
        return result;
    }

    param_min(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_normalized = this.get_param_normalized(param_o);
            if (param_o_normalized.name === param_name) {
                return param_o_normalized.min_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 0;
    }

    param_max(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_normalized = this.get_param_normalized(param_o);
            if (param_o_normalized.name === param_name) {
                return param_o_normalized.max_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 1;
    }

    param_default(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param_o = this.param_info[i];
            var param_o_normalized = this.get_param_normalized(param_o);
            if (param_o_normalized.name === param_name) {
                return param_o_normalized.default_value;
            }
        }
        console.error("Could not find param: " + param_name);
        return 0;
    }

    set_param(param_name, value, checkLocked = false) {
        if (!(param_name in this.params)) {
            console.error(`Could not set parameter (not found): ${param_name}`);
            return;
        }
        if (checkLocked) {
            if (this.locked_params[param_name]) {
                return;
            }
        }
        var min_val = this.param_min(param_name);
        var max_val = this.param_max(param_name);
        const info = this.get_param_info(param_name);
        if (info.type === "TEXT") {
            this.params[param_name] = typeof value === "string"
                ? value.slice(0, info.max_length).replace(/[\uD800-\uDBFF]$/, '') : info.default_value;
        } else if (info.type === "KNOB_TRANSITION") {
            const input = value && typeof value === "object" ? value : {start: value};
            const endpoint = (v, fallback) => Number.isFinite(v) ? Math.clamp(v, min_val, max_val) : fallback;
            this.params[param_name] = {
                start: endpoint(input.start, info.default_value_l),
                end: endpoint(input.end, info.default_value_r),
                curve: (info.curves || [info.default_tween]).includes(input.curve) ? input.curve : info.default_tween
            };
        } else if (info.type === "BUTTONSELECT") {
            this.params[param_name] = info.values.some(option => option[2] === value) ? value : info.default_value;
        } else {
            this.params[param_name] = Number.isFinite(value) ? Math.clamp(value, min_val, max_val) : this.param_default(param_name);
        }
        this.sound_params = null;
    }

    get_param(param_name) {
        if (!(param_name in this.params)) {
            console.error(`Could not get parameter (not found): ${param_name}`);
            return 0;
        }
        return this.params[param_name];
    }

    get_param_info(param_name) {
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            if (param.constructor === Array) {
                if (param[2] === param_name) {
                    return param;
                }
            } else {
                if (param.name === param_name) {
                    return param;
                }
            }
        }
        console.error(`Could not find param: ${param_name}`);
        return null;
    }

    /*********************/
    /* TEMPLATE FUNCTIONS  */
    /*********************/

    randomize_params() {
        this.reset_params(true);
        for (var i = 0; i < this.param_info.length; i++) {
            var param = this.param_info[i];
            var param_normalized = this.get_param_normalized(param);
            if (param_normalized.type === "TEXT") continue;

            var min_val = param_normalized.min_value;
            var max_val = param_normalized.max_value;
            var random_val = Math.random() * (max_val - min_val) + min_val;
            if (param_normalized.type === "KNOB_TRANSITION") {
                random_val = {start: random_val, end: Math.random() * (max_val - min_val) + min_val,
                    curve: param.curves[Math.floor(Math.random() * param.curves.length)]};
            }
            if (param_normalized.type === "BUTTONSELECT") {
                random_val = Math.floor(random_val);
                if (random_val >= max_val) {
                    random_val = max_val - 1;
                }
            }
            this.set_param(param_normalized.name, random_val,true);
        }
    }

    mutate_params() {


        for (var i = 0; i < this.param_info.length; i++) {
            if (Math.random()<0.5){
                continue;
            }
            var param = this.param_info[i];
            var param_normalized = this.get_param_normalized(param);
            if (param_normalized.type === "KNOB_TRANSITION") {
                const value = this.params[param.name];
                const delta = () => (Math.random() - 0.5) * 0.1 * (param.max - param.min);
                this.set_param(param.name, {start: value.start + delta(), end: value.end + delta(), curve: value.curve}, true);
                continue;
            }
            if (param_normalized.type !== "RANGE") {
                continue;
            }
            var min_val = param_normalized.min_value;
            var max_val = param_normalized.max_value;
            var range = max_val - min_val;
            var mutated_diff = (Math.random()-0.5)*0.1*range;
            var mutated_val = this.params[param_normalized.name] + mutated_diff;
            this.set_param(param_normalized.name, mutated_val,true);
        }

    }

    play(){
        if (this.sound){
            this.sound.stop();
        }
        this.generate_sound();
        //if sound already playing, stop it
        this.sound.play();
    }

    generate_sound_uri(){
        if (!this.sound || this.sound_params !== JSON.stringify(this.params)){
            this.generate_sound();
            this.sound_params = JSON.stringify(this.params);
        }
        return this.sound.getDataUri();
    }

    generate_sound_blob(){

        if (!this.sound){
            this.generate_sound();
        }
        var audioBuffer = this.sound;

        var channelData = [],
            totalLength = 0,
            channelLength = 0;

        for (var i = 0; i < audioBuffer.numberOfChannels; i++) {
            channelData.push(audioBuffer.getChannelData(i));
            totalLength += channelData[i].length;
            if (i == 0) channelLength = channelData[i].length;
        }

        // interleaved
        const interleaved = new Float32Array(totalLength);

        for (
            let src = 0, dst = 0;
            src < channelLength;
            src++, dst += audioBuffer.numberOfChannels
        ) {
            for (var j = 0; j < audioBuffer.numberOfChannels; j++) {
            interleaved[dst + j] = channelData[j][src];
            }
            //interleaved[dst] = left[src];
            //interleaved[dst + 1] = right[src];
        }

        // get WAV file bytes and audio params of your audio source
        const wavBytes = this.getWavBytes(interleaved.buffer, {
            isFloat: true, // floating point or 16-bit integer
            numChannels: audioBuffer.numberOfChannels,
            sampleRate: 48000,
        });
        const wav = new Blob([wavBytes], { type: "audio/wav" });
        return wav;
    }


    /*********************/
    /* CANVAS STUFF      */
    /*********************/

    generateSilhouette(height){
        var result=[];

        var buffer=this.sound.getBuffer();

        var curbar=0;
        var curmax=buffer[0];
        var curmin=buffer[0];
        var len=buffer.length;
        for (var i=0;i<len;i++){
            var val = buffer[i];
            if (i/len>curbar/height){

                if (Math.abs(curmax-curmin)<0.01){
                    curmax+=0.005;
                    curmin-=0.005;
                }

                result.push(curmax);
                result.push(curmin);
                curbar++;
                curmin=val;
                curmax=val;
            } else {
                if (val<curmin) {
                    curmin=val;
                }
                if (val>curmax) {
                    curmax=val;
                }
            }
        }
        result.push(curmax);
        result.push(curmin);

        return result;
    }

    drawWaveform(context2d){
        var w = context2d.canvas.width;
        var h = context2d.canvas.height;

        var silhouette = this.generateSilhouette(h);

        //go from top to bottom, drawing lines

        context2d.beginPath();
        context2d.lineWidth = '1'; // width of the line
        context2d.strokeStyle = '#663931'; // color of the line

        var c = w/2;
        var prev_l = 0;
        var prev_r = 0;
        for (var y=0;y<h;y++){
            var l = c+silhouette[2*y+0]*1*c;
            var r = c+silhouette[2*y+1]*1*c;
            context2d.lineTo(l,h-y);
            context2d.lineTo(r,h-y);
            prev_l = l;
            prev_r = r;
        }
        context2d.lineTo(prev_l,h-h);
        context2d.lineTo(prev_r,h-h);
        context2d.stroke();
    }


    generate_sound(){
       console.error("generate_sound not implemented");
       var tempbuffer = new Float32Array(1);
       if (this.sound){
        this.sound.stop();
       }
       this.sound = RealizedSound.from_buffer(tempbuffer);
    }

    set_sound(sound){
        if (sound){
           //pause and dispose of the old sound
        }
        this.sound = sound;
    }


    /*********************/
    /*TEMPLATE FUNCTIONS */
    /*********************/

    pick_variety(varieties){
        // each variety by default has weight 1. If the name starts with a number (possibly multiple digits), then
        //  its weight is that number
        var weights = {};
        for (var i = 0; i < varieties.length; i++) {
            var variety = varieties[i];
            var weight = 1;
            if (variety.match(/^\d+$/)) {
                weight = parseInt(variety);
            }
            weights[variety] = weight;
        }
        console.log("weights",weights);
        // now pick a variety based on the weights
        var total_weight = 0;
        for (var variety in weights) {
            total_weight += weights[variety];
        }
        var random_value = Math.random() * total_weight;
        var cumulative_weight = 0;
        for (var variety in weights) {
            cumulative_weight += weights[variety];
            if (random_value <= cumulative_weight) {
                return variety;
            }
        }
        return varieties[0];
    }
    //this actualy returns a template function ^^
    generate_template_function_from_bounds_dictionary(varieties_dictionary){
        return function(){
            var variety_names = Object.keys(varieties_dictionary);
            var picked_variety = this.pick_variety(variety_names);
            var bounds_dictionary = varieties_dictionary[picked_variety];
            for (var param_name in bounds_dictionary) {
                var possible_values = bounds_dictionary[param_name];
                var param_info = this.get_param_info(param_name);
                var param_info_normalized = this.get_param_normalized(param_info);
                switch (param_info_normalized.type) {
                    case "KNOB_TRANSITION": {
                        const sample = field => {
                            const values = possible_values.map(value => value[field]);
                            return Math.min(...values) + Math.random() * (Math.max(...values) - Math.min(...values));
                        };
                        const curve = possible_values[Math.floor(Math.random() * possible_values.length)].curve;
                        this.set_param(param_name, {start: sample("start"), end: sample("end"), curve}, true);
                        break;
                    }
                    case "BUTTONSELECT":
                        var random_value = possible_values[Math.floor(Math.random() * possible_values.length)];
                        this.set_param(param_name, random_value,true);
                        break;
                    case "RANGE":
                        var smallest_value = Math.min(...possible_values);
                        var largest_value = Math.max(...possible_values);
                        var random_value = Math.random() * (largest_value - smallest_value) + smallest_value;
                        this.set_param(param_name, random_value,true);
                        break;
                    default:
                        console.error(`Unknown param type: ${param_info.type}`);
                }
            }
        }
    }


    locked_param(param_name){
        if (this.permalocked.includes(param_name)){
            return true;
        }
        return this.locked_params[param_name];
    }

    set_locked_param(param_name,value){
        if (this.permalocked.includes(param_name)){
            this.locked_params[param_name] = true;
            return;
        }
        this.locked_params[param_name] = value;
    }

    //when passed another param dictionary, lerps the values of this synth towards the values provided
    lerp_params(other_params,amount){
        for (var param_name in other_params) {
            //get param info
            var param_info = this.get_param_info(param_name);
            //if array, continue
            if (param_info.constructor !== Array) {
                continue;
            }
            var other_param_value = other_params[param_name];
            var this_param_value = this.get_param(param_name);
            var lerped_value = this_param_value + (other_param_value - this_param_value) * amount;
            this.set_param(param_name, lerped_value,true);
        }
    }
}

// js/synths/PresetSynth.js
// Category buttons specify ranges, so every click is a new sound in that family.
class PresetSynth extends SynthBase {
    version = '1.0.0';
    header_properties = [];
    permalocked = ['masterVolume'];
    hide_params = ['masterVolume'];
    recipes = [];
    static common_params = [
        ['Sound Volume', 'Overall volume of this sound.', 'masterVolume', 0.5, 0, 1],
        ['Variation', 'A repeatable variation of the texture. Preset buttons choose a fresh one.', 'seed', 0.5, 0, 1]
    ];

    initialize_presets() {
        this.post_initialize();
        this.templates = this.recipes.map(recipe => {
            const method = 'generate_' + recipe.id;
            this[method] = () => this.generate_recipe(recipe.id);
            return [recipe.name, recipe.tip || 'Generate another ' + recipe.name.toLowerCase() + '.', method, recipe.name.replace(/[^a-zA-Z0-9]/g, '')];
        });
        this.templates.push(['Randomize','Explore all unlocked controls.','randomize_params','Random'],
            ['Mutate','Nudge the unlocked controls of this sound.','mutate_params','Mutant']);
    }

    apply_params(params, check_locked = false) {
        if (!params || typeof params !== 'object') return;
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params, name)) this.set_param(name, params[name], check_locked);
        }
    }

    generate_recipe(id) {
        const recipe = this.recipes.find(entry => entry.id === id);
        if (!recipe) return;
        this.reset_params(true);
        for (const [name, range] of Object.entries(recipe.values)) {
            const info = this.get_param_info(name);
            let value = range;
            if (Array.isArray(range)) {
                value = info.type === 'BUTTONSELECT' ? range[Math.floor(Math.random() * range.length)]
                    : range[0] + Math.random() * (range[1] - range[0]);
            }
            this.set_param(name, value, true);
        }
        this.set_param('seed', Math.random(), true);
        if (this.after_recipe) this.after_recipe(recipe);
    }

    create_random_template() {
        const recipe = this.recipes[Math.floor(Math.random() * this.recipes.length)];
        this.generate_recipe(recipe.id);
        return [recipe.name.replace(/[^a-zA-Z0-9]/g,''), this.params];
    }

    render() {
        return this.constructor.DSP.render(this.params);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }

    play() {
        this.generate_sound();
        this.sound.play(this.loop_preview === true);
    }
}

// js/synths/PresetFamily.js
// Sample a measured family as a joint sound state, preserving its correlations.
// This file contains no renderer or analysis dependencies.
class PresetFamily {
    static constrain(params, family) {
        const set = (path, value) => {
            const parts = path.split('.');
            let target = params;
            for (const part of parts.slice(0, -1)) target = target[part] ||= {};
            const key = parts.at(-1);
            target[key] = Array.isArray(value) ? Math.max(value[0], Math.min(value[1], target[key])) : value;
        };
        for (const [path, value] of Object.entries(family.limits || {})) set(path, value);
        for (const [name, range] of Object.entries(family.intervals || {})) {
            const row = params[name];
            row.end = row.start + Math.max(range[0], Math.min(range[1], row.end - row.start));
            if (family.limits[name+'.end']) set(name+'.end', family.limits[name+'.end']);
        }
        return params;
    }

    static compatible(a, b) {
        if (a.waveType !== b.waveType) return false;
        if (a.waveTo !== b.waveTo) return false;
        return ['pitch','tone','vibrato','level','morph'].every(name =>
            !a[name] || !b[name] || a[name].curve === b[name].curve);
    }

    static sample(family, random = Math.random) {
        if (!family || !family.exemplars.length) throw new Error('Preset family needs exemplars');
        const anchor = family.exemplars[Math.floor(random() * family.exemplars.length)];
        const p = JSON.parse(JSON.stringify(anchor));
        const partners = family.exemplars.filter(candidate => candidate !== anchor && this.compatible(anchor, candidate));
        if (partners.length) {
            const partner = partners[Math.floor(random() * partners.length)];
            const amount = random() * 0.3;
            for (const [name, value] of Object.entries(p)) {
                if (name === 'masterVolume' || name === 'waveType') continue;
                if (typeof value === 'number' && typeof partner[name] === 'number') {
                    p[name] = value + (partner[name] - value) * amount;
                } else if (value && typeof value === 'object' && partner[name]) {
                    // Keep the anchor's curve; its discrete trajectory is part of its identity.
                    for (const side of ['start','end']) value[side] += (partner[name][side] - value[side]) * amount;
                }
            }
        }
        const offset = extent => (random() - 0.5) * extent;
        const clamp = value => Math.max(0, Math.min(1, value));
        const time = 0.85 + random() * 0.3;
        if (p.duration !== undefined) p.duration *= time;
        for (const name of ['attack','release']) if (p[name] !== undefined) p[name] *= time;
        for (const [name, standardExtent] of [['pitch',0.07],['tone',0.1],['vibrato',0.1],['level',0.1],['morph',0.06]]) {
            if (!p[name]) continue;
            const extent = family.variation?.[name] ?? standardExtent;
            const shift = offset(extent);
            for (const side of ['start','end']) p[name][side] = clamp(p[name][side] + shift);
        }
        for (const name of ['resonance','echo']) if (p[name] !== undefined) {
            // Even a little echo adds a long tail to a dry click or static fleck.
            p[name] = name === 'echo' && anchor.echo === 0 ? 0 : clamp(p[name] + offset(0.08));
        }
        return this.constrain(p, family);
    }
}

// js/synths/TransfxrPresets.js
// Curated from the survey and user listening feedback. See tools/preset_survey/family_profiles.json.
const TRANSFXR_PRESET_FAMILIES = [{"id":"bright_whistles","name":"Bright Whistles","tip":"Clear, bright electronic whistles with a clean ringing voice.","limits":{},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C001","C002","C003","C004","C005","C006","C007","C008","C009","C010","C011","C012","C013","C014","C015","C016","C017","C018","C019","C020","C021","C022","C023","C024"],"survey_source_ids":["T298","T390","T160","T148","T172","T501","T008","T188","T138","T448","T117","T442","T031","T245","T352","T130","T296","T152","T016","T286","T149","T053","T277","T047"],"exemplars":[{"masterVolume":0.5,"waveType":3,"duration":0.7198923793453867,"pitch":{"start":0.5915093034342863,"end":0.7454320507496595,"curve":"Ease Out"},"tone":{"start":0.9025093346484937,"end":0.8124980643042363,"curve":"Linear"},"vibrato":{"start":0,"end":0.8329445968847722,"curve":"Triangle"},"level":{"start":0.6518196925404481,"end":0.6677941257227212,"curve":"Steps"},"attack":0.011339501090347766,"release":0.28950706466863135,"resonance":0.5959234095178544,"echo":0,"waveTo":7,"morph":{"start":0.13158720296341925,"end":0.0674891445832327,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":3,"duration":1.2616396003107162,"pitch":{"start":0.7413998163398355,"end":0.7499275303538888,"curve":"Ease In"},"tone":{"start":0.9156018541427329,"end":0.38497373885475095,"curve":"Ease In"},"vibrato":{"start":0,"end":0.4960012100636959,"curve":"Ease In"},"level":{"start":0.883780780993402,"end":0.7811754090618342,"curve":"Triangle"},"attack":0.37673513261846,"release":0.803557245823838,"resonance":0.35009414069354533,"echo":0.6949854749953374,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.39011433873746143,"pitch":{"start":0.871931469712872,"end":0.7815329354256392,"curve":"Steps"},"tone":{"start":0.6208185920142569,"end":0.9418061487493106,"curve":"Steps"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.46460112619679417,"end":0.47162472464144234,"curve":"Ease Out"},"attack":0.013971194935496896,"release":0.07734826137519078,"resonance":0.5901544214691966,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.22617629347063653,"pitch":{"start":0.596909168183338,"end":0.7242542336322367,"curve":"Triangle"},"tone":{"start":0.19575052807340398,"end":0.9245920453220606,"curve":"Steps"},"vibrato":{"start":0,"end":0.02666174480691552,"curve":"Triangle"},"level":{"start":0.5977368503808975,"end":0.9059688679967075,"curve":"Ease Out"},"attack":0.056339468136328674,"release":0.13190540234189582,"resonance":0.3492941131698899,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.9069041447013533,"pitch":{"start":0.8140593467233703,"end":0.6458463167957962,"curve":"Ease Out"},"tone":{"start":0.17045726939104497,"end":0.208658335194923,"curve":"Linear"},"vibrato":{"start":0.06902710581198335,"end":0,"curve":"Smooth"},"level":{"start":0.9906108000315725,"end":0.648119955630973,"curve":"Ease Out"},"attack":0.010573208265937864,"release":0.30209461445151103,"resonance":0.12231203763512893,"echo":0,"waveTo":7,"morph":{"start":0.005001974529586732,"end":0.01832050960045308,"curve":"Ease Out"}},{"masterVolume":0.5,"waveType":1,"duration":0.5579809247746218,"pitch":{"start":0.7763675379101187,"end":1,"curve":"Triangle"},"tone":{"start":0.4568156120833009,"end":1,"curve":"Linear"},"vibrato":{"start":0.29404062482062726,"end":0.753931316616945,"curve":"Ease In"},"level":{"start":0.8983975612325594,"end":0.5491120676277206,"curve":"Ease In"},"attack":0.015217661584762412,"release":0.15217661584762412,"resonance":0.6274445922463201,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.10658784431871027,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.9351163391628037,"pitch":{"start":0.6737039160146379,"end":0.9287649361696094,"curve":"Ease In"},"tone":{"start":0.4374400643981062,"end":0.31938879350200294,"curve":"Triangle"},"vibrato":{"start":0.5425216241274029,"end":0.15860732458531857,"curve":"Steps"},"level":{"start":0.6241556011489593,"end":0.7548746941238642,"curve":"Pulse"},"attack":0.23040631748435622,"release":0.7266464097465928,"resonance":0.19725841730833052,"echo":0.5701446531456895,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":2.2103310736050634,"pitch":{"start":0.8817162727774122,"end":0.8743998907785863,"curve":"Bounce"},"tone":{"start":0.4392971091205254,"end":0.735157434816938,"curve":"Bounce"},"vibrato":{"start":0,"end":0.12345174606889486,"curve":"Bounce"},"level":{"start":0.7213386167539284,"end":0.7996966253034771,"curve":"Ease Out"},"attack":0.017707366998307404,"release":1,"resonance":0.624685716163367,"echo":0,"waveTo":7,"morph":{"start":0.14358603209257126,"end":0.11690602515358478,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":3,"duration":1.8235864412816292,"pitch":{"start":0.7996315787988715,"end":0.6593648271169513,"curve":"Ease Out"},"tone":{"start":0.7596986487507821,"end":0.132740231056232,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.44707809073152016,"end":0.3186337531544268,"curve":"Ease Out"},"attack":0.005370622909627854,"release":0.7925737447517136,"resonance":0.9131058977451175,"echo":0.14483053085859865,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.45796871006303086,"pitch":{"start":0.5987893511471338,"end":0.7031857626140118,"curve":"Steps"},"tone":{"start":0.8348633465007879,"end":0.49325000067474317,"curve":"Ease In"},"vibrato":{"start":0,"end":0,"curve":"Ease Out"},"level":{"start":0.43486739407526326,"end":0.14569749825634062,"curve":"Ease In"},"attack":0.19159553053181508,"release":0.17050405858864429,"resonance":0.26058842925122006,"echo":0.6471226267516612,"waveTo":7,"morph":{"start":0.1346860361751169,"end":0.05367504275403917,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.6154133030801662,"pitch":{"start":0.7747974642831832,"end":1,"curve":"Ease In"},"tone":{"start":0.7043202309170737,"end":1,"curve":"Linear"},"vibrato":{"start":0.08279161162208766,"end":0.6825835735769943,"curve":"Ease In"},"level":{"start":0.9021654267096892,"end":0.54831386806909,"curve":"Linear"},"attack":0.016783999174913623,"release":0.16783999174913622,"resonance":0.5355560399708338,"echo":0.3836281942599454,"waveTo":7,"morph":{"start":0,"end":0.1075618825852871,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":1.0237422914944596,"pitch":{"start":0.8365203464403749,"end":0.5848989852145314,"curve":"Bounce"},"tone":{"start":0.5743756029754877,"end":0.7490246720495634,"curve":"Pulse"},"vibrato":{"start":0.5042412532493472,"end":0,"curve":"Ease Out"},"level":{"start":0.8232393337762914,"end":0.12171025371178984,"curve":"Smooth"},"attack":0.01022392084915191,"release":0.6380137576549229,"resonance":0.04222827232442796,"echo":0.4420782300876453,"waveTo":7,"morph":{"start":0.04095241210889071,"end":0.1358125047851354,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":3,"duration":0.3289023176257494,"pitch":{"start":0.8406871235556901,"end":0.9064801402762532,"curve":"Steps"},"tone":{"start":0.45818038521101695,"end":0.8334039261448197,"curve":"Smooth"},"vibrato":{"start":0.2578656852710992,"end":0.004326007328927517,"curve":"Ease Out"},"level":{"start":0.6718035156838595,"end":0.5652783123310655,"curve":"Bounce"},"attack":0.13285102948735047,"release":0.20449489972166018,"resonance":0.2811315391794778,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.31672144660205376,"pitch":{"start":0.6904776146914811,"end":0.920477614691481,"curve":"Triangle"},"tone":{"start":0.6377729904372245,"end":0.7548388142604381,"curve":"Linear"},"vibrato":{"start":0,"end":0.8530793740181253,"curve":"Ease In"},"level":{"start":0.8973670928506181,"end":0.3568767692893744,"curve":"Linear"},"attack":0.008637857634601466,"release":0.08637857634601466,"resonance":0.30075077353976665,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.1480662397807464,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.22092738187321964,"pitch":{"start":0.7880481295078062,"end":0.836664601555094,"curve":"Steps"},"tone":{"start":0.5818433610023931,"end":0.9326221556519159,"curve":"Smooth"},"vibrato":{"start":0,"end":0.7999256683979183,"curve":"Steps"},"level":{"start":0.942814314190764,"end":0.19689586261287334,"curve":"Ease In"},"attack":0.034572725848130016,"release":0.05420691236222191,"resonance":0.7489369819988496,"echo":0,"waveTo":7,"morph":{"start":0.3703020401299,"end":0.42163698305375874,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.28179455439208584,"pitch":{"start":0.6825075632845983,"end":0.8864307298511266,"curve":"Linear"},"tone":{"start":0.3167670641792938,"end":0.9548864028649404,"curve":"Steps"},"vibrato":{"start":0.017701273318380117,"end":0.34795926534570754,"curve":"Pulse"},"level":{"start":0.8334570411010644,"end":0.813731804061681,"curve":"Smooth"},"attack":0.002393562220036983,"release":0.17233965684895675,"resonance":0.11116838996531442,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.8983321287631666,"pitch":{"start":0.8196474792854861,"end":0.6909950042609125,"curve":"Ease In"},"tone":{"start":0.9470346098882146,"end":0.32963579138740895,"curve":"Ease In"},"vibrato":{"start":0.4921712221112102,"end":0.435970721533522,"curve":"Ease In"},"level":{"start":0.598358640121296,"end":0.43687159025110306,"curve":"Steps"},"attack":0.1950747837904561,"release":0.2163977032801768,"resonance":0.5865595372510143,"echo":0,"waveTo":7,"morph":{"start":0.10149763884954155,"end":0.17361429539043458,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":1,"duration":0.9290700355923286,"pitch":{"start":0.8158280691783876,"end":0.9317100461013614,"curve":"Pulse"},"tone":{"start":0.8158852875581942,"end":0.7440430712304078,"curve":"Steps"},"vibrato":{"start":0,"end":0,"curve":"Ease In"},"level":{"start":0.8220638294122182,"end":0.7967283200565726,"curve":"Bounce"},"attack":0.012223343531135468,"release":0.611607292976424,"resonance":0.031166910985484717,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.5983789154224881,"pitch":{"start":0.7281305085215718,"end":0.8360306794568896,"curve":"Smooth"},"tone":{"start":0.5304497849545442,"end":0.45908731741365044,"curve":"Pulse"},"vibrato":{"start":0.137719564139843,"end":0,"curve":"Linear"},"level":{"start":0.9567440885468386,"end":0.4760956065356732,"curve":"Pulse"},"attack":0.002663910050410777,"release":0.4619491709119182,"resonance":0.6491728248074651,"echo":0.6473156193504109,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":2,"duration":0.3964564014263349,"pitch":{"start":0.6655410013790243,"end":0.8472536161448806,"curve":"Steps"},"tone":{"start":0.5164787797257304,"end":0.6063426624750718,"curve":"Triangle"},"vibrato":{"start":0.5336033024359494,"end":0,"curve":"Bounce"},"level":{"start":0.8257627902552485,"end":0.9039523765072226,"curve":"Ease In"},"attack":0.037688949028927526,"release":0.19661019620345052,"resonance":0.5370941197732463,"echo":0.1011749772937037,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.7737497785241391,"pitch":{"start":0.5613467188458889,"end":0.7913467188458889,"curve":"Triangle"},"tone":{"start":0.6703743332065641,"end":0.8230733892414719,"curve":"Linear"},"vibrato":{"start":0,"end":0.7851998098893092,"curve":"Ease In"},"level":{"start":0.8540916387690232,"end":0.6930641462793574,"curve":"Linear"},"attack":0.021102266687021975,"release":0.21102266687021973,"resonance":0.6407187991659157,"echo":0,"waveTo":7,"morph":{"start":0.0742145529948175,"end":0,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.39271633906140374,"pitch":{"start":0.6570676721073687,"end":0.8870676721073687,"curve":"Triangle"},"tone":{"start":0.5945765245007351,"end":1,"curve":"Linear"},"vibrato":{"start":0,"end":0.760776501451619,"curve":"Ease In"},"level":{"start":0.7446874990826473,"end":0.4809934034245089,"curve":"Ease In"},"attack":0.010710445610765557,"release":0.10710445610765557,"resonance":0.0002558396779932082,"echo":0.5991153970849701,"waveTo":7,"morph":{"start":0.098683335701935,"end":0,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":1,"duration":0.8662148159287244,"pitch":{"start":0.6185958941746503,"end":0.8485958941746503,"curve":"Triangle"},"tone":{"start":0.6582157318945974,"end":0.9842331428080797,"curve":"Linear"},"vibrato":{"start":0,"end":0.9505158361978829,"curve":"Ease In"},"level":{"start":1,"end":0.6195505921030418,"curve":"Linear"},"attack":0.023624040434419756,"release":0.23624040434419755,"resonance":0.19416059323120863,"echo":0.1172218718705699,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.6907745539958704,"pitch":{"start":0.686500835758634,"end":0.7796109938807785,"curve":"Smooth"},"tone":{"start":0.6098805632907898,"end":0.29010511426022273,"curve":"Steps"},"vibrato":{"start":0.12773322686553001,"end":0,"curve":"Triangle"},"level":{"start":0.779131185321603,"end":0.7285123393591493,"curve":"Steps"},"attack":0.19812160102627896,"release":0.25290447530999766,"resonance":0.7010447081527672,"echo":0.35398677166085685,"waveTo":7,"morph":{"start":0.20865654561668634,"end":0.04965760681312531,"curve":"Bounce"}}]},{"id":"grainy_taps","name":"Grainy Taps","tip":"Dry, low gritty taps. A single quick attack, with no long tail.","limits":{"waveTo":7,"waveType":2,"duration":[0.065,0.17],"attack":[0.001,0.006],"release":[0.045,0.14],"echo":0,"resonance":[0.12,0.4],"pitch.start":[0.34,0.48],"pitch.end":[0.27,0.43],"pitch.curve":"Ease Out","tone.start":[0.32,0.52],"tone.end":[0.28,0.46],"tone.curve":"Ease Out","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.7,0.95],"level.end":[0.08,0.25],"level.curve":"Ease Out","morph.start":[0.72,0.92],"morph.end":[0.65,0.85],"morph.curve":"Linear"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C025","C026","C027","C028","C029","C030","C031","C032","C033","C034","C035","C036"],"survey_source_ids":["T248","T275","T065","T450","T218","T178","T374","T210","T347","T353","T290","T193"],"exemplars":[{"masterVolume":0.5,"waveType":2,"duration":0.09232875395388072,"pitch":{"start":0.38291498312992744,"end":0.38563345308629543,"curve":"Ease Out"},"tone":{"start":0.4012288945675907,"end":0.29204868506677095,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9352545766880752,"end":0.25,"curve":"Ease Out"},"attack":0.004149721182265588,"release":0.09787003396237418,"resonance":0.2319835468643145,"echo":0,"waveTo":7,"morph":{"start":0.92,"end":0.8035996540700157,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.1074739039771091,"pitch":{"start":0.4677965061734346,"end":0.2885456151850409,"curve":"Ease Out"},"tone":{"start":0.4925685153532541,"end":0.3981103874049238,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8193055637670281,"end":0.24804818240539706,"curve":"Ease Out"},"attack":0.006,"release":0.12872547050166455,"resonance":0.18741136025028216,"echo":0,"waveTo":7,"morph":{"start":0.72,"end":0.65,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.065,"pitch":{"start":0.4766648603891166,"end":0.2994342157319285,"curve":"Ease Out"},"tone":{"start":0.52,"end":0.2851538290294452,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.95,"end":0.19072561179372888,"curve":"Ease Out"},"attack":0.001,"release":0.05929254502433798,"resonance":0.3957010134002175,"echo":0,"waveTo":7,"morph":{"start":0.72,"end":0.6963692998299464,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.065,"pitch":{"start":0.35173372151238336,"end":0.35175140254994686,"curve":"Ease Out"},"tone":{"start":0.32,"end":0.46,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7,"end":0.25,"curve":"Ease Out"},"attack":0.003616408742429892,"release":0.07238241131862894,"resonance":0.39182616642412765,"echo":0,"waveTo":7,"morph":{"start":0.8500611062176493,"end":0.8147220196942382,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.17,"pitch":{"start":0.44095008283184917,"end":0.3567814580138951,"curve":"Ease Out"},"tone":{"start":0.3806113164397872,"end":0.3164466588205809,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7546489226630861,"end":0.12785884769800246,"curve":"Ease Out"},"attack":0.0014185936402695872,"release":0.14,"resonance":0.2058624686454934,"echo":0,"waveTo":7,"morph":{"start":0.9084291280526264,"end":0.8303186440457003,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.06545227422651981,"pitch":{"start":0.34,"end":0.4261012290555658,"curve":"Ease Out"},"tone":{"start":0.32625576713397353,"end":0.28,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8572412440124718,"end":0.16178750637857547,"curve":"Ease Out"},"attack":0.005203459246118332,"release":0.06565515396682528,"resonance":0.271585816018437,"echo":0,"waveTo":7,"morph":{"start":0.7665988292683694,"end":0.6591072461676205,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.07256615492433088,"pitch":{"start":0.44839172287152745,"end":0.27,"curve":"Ease Out"},"tone":{"start":0.32,"end":0.28,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.95,"end":0.09371670392256362,"curve":"Ease Out"},"attack":0.002776047798927568,"release":0.045,"resonance":0.12565535502071742,"echo":0,"waveTo":7,"morph":{"start":0.9028267881879811,"end":0.85,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.17,"pitch":{"start":0.34,"end":0.43,"curve":"Ease Out"},"tone":{"start":0.4929398221181823,"end":0.34670542943754856,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.828165730895214,"end":0.08,"curve":"Ease Out"},"attack":0.0021849645036052245,"release":0.14,"resonance":0.12,"echo":0,"waveTo":7,"morph":{"start":0.92,"end":0.7271136412287713,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09850554020900727,"pitch":{"start":0.39600093344011505,"end":0.27,"curve":"Ease Out"},"tone":{"start":0.4583391720479593,"end":0.45521943000947174,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8679425579813274,"end":0.11046614206728306,"curve":"Ease Out"},"attack":0.006,"release":0.09940587705143895,"resonance":0.12,"echo":0,"waveTo":7,"morph":{"start":0.8637748171275553,"end":0.85,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.11603833526790655,"pitch":{"start":0.48,"end":0.326948010655409,"curve":"Ease Out"},"tone":{"start":0.52,"end":0.3019238182090416,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.853333787158639,"end":0.16594604221300446,"curve":"Ease Out"},"attack":0.001,"release":0.12137002846533734,"resonance":0.4,"echo":0,"waveTo":7,"morph":{"start":0.7785122011456473,"end":0.6777244729163983,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09127564467082445,"pitch":{"start":0.35019756539108204,"end":0.43,"curve":"Ease Out"},"tone":{"start":0.3921097673722759,"end":0.46,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7,"end":0.19204062403053168,"curve":"Ease Out"},"attack":0.005838654267255103,"release":0.045,"resonance":0.4,"echo":0,"waveTo":7,"morph":{"start":0.7207728097340701,"end":0.655942637545699,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.1156489409205854,"pitch":{"start":0.48,"end":0.3034611564840904,"curve":"Ease Out"},"tone":{"start":0.4316823936008703,"end":0.32696706071949,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8918233905692706,"end":0.08,"curve":"Ease Out"},"attack":0.001,"release":0.12095993439589353,"resonance":0.22615462475790118,"echo":0,"waveTo":7,"morph":{"start":0.7522619452950622,"end":0.65,"curve":"Linear"}}]},{"id":"rocket_zips","name":"Rocket Zips","tip":"A short hollow arcade whistle that rockets upwards and cuts off.","limits":{"waveType":3,"duration":[0.22,0.4],"attack":[0.001,0.008],"release":[0.1,0.25],"echo":0,"resonance":[0.08,0.3],"pitch.start":[0.14,0.27],"pitch.end":[0.64,0.8],"pitch.curve":"Ease Out","tone.start":[0.65,0.85],"tone.end":[0.78,0.95],"tone.curve":"Linear","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.65,0.85],"level.end":[0.3,0.6],"level.curve":"Linear"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C037","C038","C039","C040","C041","C042","C043","C044","C045","C046","C047","C048"],"survey_source_ids":["T035","T387","T015","T284","T030","T271","T414","T460","T027","T270","T157","T424"],"exemplars":[{"masterVolume":0.5,"waveType":3,"duration":0.2753738638128379,"pitch":{"start":0.14,"end":0.664136208135397,"curve":"Ease Out"},"tone":{"start":0.6657503983272545,"end":0.8287610305095069,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7243706951711208,"end":0.49519688735716,"curve":"Linear"},"attack":0.004230336387374148,"release":0.1694135296724525,"resonance":0.16781403159524116,"echo":0,"waveTo":7,"morph":{"start":0.022942001615789322,"end":0.009847400731886842,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.2385847474961694,"pitch":{"start":0.23210351832620224,"end":0.7383264777976872,"curve":"Ease Out"},"tone":{"start":0.8030822010831332,"end":0.7811747932700207,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8185584182086717,"end":0.3767500826055493,"curve":"Linear"},"attack":0.005359640985931203,"release":0.16047161147064948,"resonance":0.18580583350303279,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.240043938484892,"pitch":{"start":0.14498291609090086,"end":0.7702670181496699,"curve":"Ease Out"},"tone":{"start":0.85,"end":0.78,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.65,"end":0.3,"curve":"Linear"},"attack":0.003145772637875725,"release":0.14701003624583855,"resonance":0.16601062446828202,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.22,"pitch":{"start":0.21811028926249743,"end":0.64,"curve":"Ease Out"},"tone":{"start":0.65,"end":0.8175530345160416,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.666654662361639,"end":0.40300236679262424,"curve":"Linear"},"attack":0.0011735906600658435,"release":0.1,"resonance":0.18829921394300608,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.2311595442353811,"pitch":{"start":0.16340818397504847,"end":0.7430808083971023,"curve":"Ease Out"},"tone":{"start":0.7113497334367541,"end":0.95,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.65,"end":0.6,"curve":"Linear"},"attack":0.0073426421804965785,"release":0.14940885322205016,"resonance":0.09845895574994226,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.23147241093075702,"pitch":{"start":0.27,"end":0.783790964077353,"curve":"Ease Out"},"tone":{"start":0.7856895118952452,"end":0.95,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8310136064851508,"end":0.4067462200625409,"curve":"Linear"},"attack":0.0011483624868620752,"release":0.1,"resonance":0.08,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.22,"pitch":{"start":0.2083093769167167,"end":0.7617428891731954,"curve":"Ease Out"},"tone":{"start":0.85,"end":0.8176373914863071,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7103134539934393,"end":0.5049510911822163,"curve":"Linear"},"attack":0.001,"release":0.12003942950191554,"resonance":0.08,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.24920649136333645,"pitch":{"start":0.17048159520847214,"end":0.7462296638407879,"curve":"Ease Out"},"tone":{"start":0.7591902470483137,"end":0.9316417517818545,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.85,"end":0.3,"curve":"Linear"},"attack":0.0010758284954093722,"release":0.14891186676270007,"resonance":0.24684061476283703,"echo":0,"waveTo":7,"morph":{"start":0.05,"end":0.05,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.3461220128557365,"pitch":{"start":0.27,"end":0.8,"curve":"Ease Out"},"tone":{"start":0.8344622561766853,"end":0.8165377676391464,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.85,"end":0.5901207958332353,"curve":"Linear"},"attack":0.001,"release":0.25,"resonance":0.3,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.2476928717239019,"pitch":{"start":0.17232003563219575,"end":0.8,"curve":"Ease Out"},"tone":{"start":0.7873978828958418,"end":0.78,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7239244968054304,"end":0.4271639514884954,"curve":"Linear"},"attack":0.008,"release":0.15108497112553326,"resonance":0.09655149535350757,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.4,"pitch":{"start":0.21056703516438147,"end":0.64,"curve":"Ease Out"},"tone":{"start":0.65,"end":0.883070289726012,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8033319538288248,"end":0.6,"curve":"Linear"},"attack":0.0073917983890130655,"release":0.25,"resonance":0.2427822756792823,"echo":0,"waveTo":7,"morph":{"start":0.05,"end":0.05,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.4,"pitch":{"start":0.14,"end":0.6803880664856284,"curve":"Ease Out"},"tone":{"start":0.6842454141452741,"end":0.8437990671722172,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7015371740674698,"end":0.3740866746739956,"curve":"Linear"},"attack":0.008,"release":0.1756314728198054,"resonance":0.3,"echo":0,"waveTo":7,"morph":{"start":0.008993005538836014,"end":0.012108784605056018,"curve":"Linear"}}]},{"id":"wavering_calls","name":"Wavering Calls","tip":"A rounded voice with an audible, steady quiver throughout the call.","limits":{"waveType":1,"duration":[0.7,1.2],"attack":[0.025,0.08],"release":[0.18,0.4],"echo":0,"resonance":[0.08,0.3],"pitch.start":[0.38,0.55],"pitch.end":[0.31,0.62],"pitch.curve":"Smooth","tone.start":[0.6,0.78],"tone.end":[0.58,0.75],"tone.curve":"Smooth","vibrato.start":[0.72,0.9],"vibrato.end":[0.72,0.9],"vibrato.curve":"Linear","level.start":[0.6,0.8],"level.end":[0.4,0.65],"level.curve":"Smooth"},"intervals":{"pitch":[-0.07,0.07]},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C049","C050","C051","C052","C053","C054","C055","C056","C057","C058","C059","C060"],"survey_source_ids":["T181","T013","T136","T204","T429","T469","T307","T341","T472","T336","T186","T346"],"exemplars":[{"masterVolume":0.5,"waveType":1,"duration":0.8560486367886412,"pitch":{"start":0.48052039991556195,"end":0.5505203999155619,"curve":"Smooth"},"tone":{"start":0.6742921627681343,"end":0.75,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.9,"curve":"Linear"},"level":{"start":0.7805979756239257,"end":0.4034200696366278,"curve":"Smooth"},"attack":0.027427830724858524,"release":0.20983089551082398,"resonance":0.08,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.026527721666923423,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.7358054920065776,"pitch":{"start":0.3969262647802915,"end":0.46692626478029153,"curve":"Smooth"},"tone":{"start":0.6502796099837488,"end":0.7343538750631068,"curve":"Smooth"},"vibrato":{"start":0.9,"end":0.72,"curve":"Linear"},"level":{"start":0.7549252405297562,"end":0.6479577105087564,"curve":"Smooth"},"attack":0.02508961863361136,"release":0.1829999621443468,"resonance":0.08,"echo":0,"waveTo":7,"morph":{"start":0.016165296397871846,"end":0.02909172607406498,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":1.0692744991784302,"pitch":{"start":0.48077738090007405,"end":0.550777380900074,"curve":"Smooth"},"tone":{"start":0.7466290725293332,"end":0.58,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.753895405643803,"curve":"Linear"},"level":{"start":0.705400892977945,"end":0.4,"curve":"Smooth"},"attack":0.02505812821185352,"release":0.28461938703391565,"resonance":0.16756356397323657,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.8260544960902485,"pitch":{"start":0.431970195885257,"end":0.4182252037145771,"curve":"Smooth"},"tone":{"start":0.7379414628911983,"end":0.611244502353158,"curve":"Smooth"},"vibrato":{"start":0.9,"end":0.72,"curve":"Linear"},"level":{"start":0.7010516526034816,"end":0.65,"curve":"Smooth"},"attack":0.08,"release":0.32393209095542763,"resonance":0.3,"echo":0,"waveTo":7,"morph":{"start":0.06,"end":0.06,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.7,"pitch":{"start":0.38,"end":0.45,"curve":"Smooth"},"tone":{"start":0.6527767493889685,"end":0.75,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.7506601495403855,"curve":"Linear"},"level":{"start":0.6942186128512773,"end":0.65,"curve":"Smooth"},"attack":0.025,"release":0.18,"resonance":0.2677400017936274,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.0034284984826745916,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.7,"pitch":{"start":0.49914432456845775,"end":0.5691443245684578,"curve":"Smooth"},"tone":{"start":0.78,"end":0.721920219121037,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.8904719935883832,"curve":"Linear"},"level":{"start":0.6691481037231581,"end":0.4,"curve":"Smooth"},"attack":0.026575703210805008,"release":0.19135366089952757,"resonance":0.3,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.027304796502573208,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":1.2,"pitch":{"start":0.38,"end":0.45,"curve":"Smooth"},"tone":{"start":0.6,"end":0.7378482293021783,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.72,"curve":"Linear"},"level":{"start":0.6,"end":0.4403419375997504,"curve":"Smooth"},"attack":0.025,"release":0.4,"resonance":0.1524338878797447,"echo":0,"waveTo":7,"morph":{"start":0.012952229786120753,"end":0.0018142563904576256,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.7851547440941099,"pitch":{"start":0.49736990517580726,"end":0.5673699051758072,"curve":"Smooth"},"tone":{"start":0.78,"end":0.75,"curve":"Smooth"},"vibrato":{"start":0.7582322972121568,"end":0.8989854694460633,"curve":"Linear"},"level":{"start":0.7142650717455137,"end":0.5130595945163949,"curve":"Smooth"},"attack":0.027091641607670313,"release":0.20254108842256108,"resonance":0.1534303848113145,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":1.2,"pitch":{"start":0.55,"end":0.48000000000000004,"curve":"Smooth"},"tone":{"start":0.6,"end":0.58,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.9,"curve":"Linear"},"level":{"start":0.8,"end":0.5724739383831823,"curve":"Smooth"},"attack":0.027246489526819767,"release":0.2511566364608444,"resonance":0.2490084259121515,"echo":0,"waveTo":7,"morph":{"start":0.014813075543160742,"end":0.035600268781084264,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":1.0397680532078075,"pitch":{"start":0.55,"end":0.48000000000000004,"curve":"Smooth"},"tone":{"start":0.6509612568702926,"end":0.6072089541312689,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.72,"curve":"Linear"},"level":{"start":0.8,"end":0.6496245866826055,"curve":"Smooth"},"attack":0.02569016779501449,"release":0.4,"resonance":0.26162965096168894,"echo":0,"waveTo":7,"morph":{"start":0.03091132819479316,"end":0.06,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.8010689412751139,"pitch":{"start":0.46162312424422663,"end":0.49175615319305377,"curve":"Smooth"},"tone":{"start":0.7029158839787109,"end":0.696712678331333,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.72,"curve":"Linear"},"level":{"start":0.6,"end":0.4111254400522906,"curve":"Smooth"},"attack":0.055701348983307614,"release":0.18,"resonance":0.11330399379476938,"echo":0,"waveTo":7,"morph":{"start":0.013446637143120624,"end":0.015746147781251267,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":1.0486005092016941,"pitch":{"start":0.49673760010767465,"end":0.45305485360224135,"curve":"Smooth"},"tone":{"start":0.622344919384309,"end":0.5943684275888904,"curve":"Smooth"},"vibrato":{"start":0.72,"end":0.72,"curve":"Linear"},"level":{"start":0.6992371342235625,"end":0.6277270007930247,"curve":"Smooth"},"attack":0.08,"release":0.25921547726534,"resonance":0.11873406646772283,"echo":0,"waveTo":7,"morph":{"start":0.06,"end":0.05569480396923406,"curve":"Linear"}}]},{"id":"fuzzy_chirps","name":"Fuzzy Chirps","tip":"Tiny bright buzzes with a pitched chirp inside a fuzzy edge.","limits":{"waveTo":7,"waveType":2,"duration":[0.09,0.25],"attack":[0.001,0.006],"release":[0.055,0.16],"echo":0,"resonance":[0.12,0.35],"pitch.start":[0.57,0.7],"pitch.end":[0.69,0.8],"pitch.curve":"Pulse","tone.start":[0.68,0.88],"tone.end":[0.6,0.8],"tone.curve":"Ease Out","vibrato.start":[0,0.12],"vibrato.end":[0,0.12],"vibrato.curve":"Linear","level.start":[0.6,0.8],"level.end":[0.15,0.35],"level.curve":"Ease Out","morph.start":[0.2,0.38],"morph.end":[0.2,0.38],"morph.curve":"Linear"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C061","C062","C063","C064","C065","C066","C067","C068","C069","C070","C071","C072"],"survey_source_ids":["T022","T312","T308","T066","T488","T054","T213","T334","T108","T224","T511","T389"],"exemplars":[{"masterVolume":0.5,"waveType":2,"duration":0.09079405408980269,"pitch":{"start":0.6003300084466394,"end":0.772970248106413,"curve":"Pulse"},"tone":{"start":0.68,"end":0.7749303435413937,"curve":"Ease Out"},"vibrato":{"start":0.12,"end":0.12,"curve":"Linear"},"level":{"start":0.7544641280857771,"end":0.18210229263441918,"curve":"Ease Out"},"attack":0.003295022518737541,"release":0.05698427111568171,"resonance":0.16031662274016156,"echo":0,"waveTo":7,"morph":{"start":0.2,"end":0.2,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.10040226897888593,"pitch":{"start":0.5825999202047614,"end":0.783341213261652,"curve":"Pulse"},"tone":{"start":0.8786863694964504,"end":0.7097756170555491,"curve":"Ease Out"},"vibrato":{"start":0.10058629627431039,"end":0,"curve":"Linear"},"level":{"start":0.6,"end":0.1952339482769121,"curve":"Ease Out"},"attack":0.004869863088654546,"release":0.055,"resonance":0.17818351285471995,"echo":0,"waveTo":7,"morph":{"start":0.2444913786172213,"end":0.2,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.1132276818951711,"pitch":{"start":0.5907750710789044,"end":0.7961751423176098,"curve":"Pulse"},"tone":{"start":0.8100736700532728,"end":0.8,"curve":"Ease Out"},"vibrato":{"start":0.11634505759823716,"end":0.11765650966492146,"curve":"Linear"},"level":{"start":0.7136478330546112,"end":0.35,"curve":"Ease Out"},"attack":0.006,"release":0.06356328807163897,"resonance":0.12,"echo":0,"waveTo":7,"morph":{"start":0.2211379862230637,"end":0.2245309247463382,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09,"pitch":{"start":0.57,"end":0.788811242304113,"curve":"Pulse"},"tone":{"start":0.8136323276383134,"end":0.6,"curve":"Ease Out"},"vibrato":{"start":0.012490524215465594,"end":0,"curve":"Linear"},"level":{"start":0.7424831153818161,"end":0.15,"curve":"Ease Out"},"attack":0.006,"release":0.06138682055761533,"resonance":0.35,"echo":0,"waveTo":7,"morph":{"start":0.3078829147601425,"end":0.2958702449941061,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.15582776639490423,"pitch":{"start":0.6338517444751647,"end":0.69,"curve":"Pulse"},"tone":{"start":0.8192451502568854,"end":0.6105421634370908,"curve":"Ease Out"},"vibrato":{"start":0,"end":0.0935499685055099,"curve":"Linear"},"level":{"start":0.6,"end":0.15993293118437873,"curve":"Ease Out"},"attack":0.001,"release":0.06813749447137321,"resonance":0.35,"echo":0,"waveTo":7,"morph":{"start":0.37431158385309427,"end":0.38,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09,"pitch":{"start":0.7,"end":0.7514377461344937,"curve":"Pulse"},"tone":{"start":0.8693920686951917,"end":0.6,"curve":"Ease Out"},"vibrato":{"start":0.12,"end":0.008240119784365714,"curve":"Linear"},"level":{"start":0.8,"end":0.22374280581711287,"curve":"Ease Out"},"attack":0.0045142710085035506,"release":0.055,"resonance":0.29327035944587165,"echo":0,"waveTo":7,"morph":{"start":0.22025070839136876,"end":0.2233685677511641,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.11100031845380454,"pitch":{"start":0.6506798896108932,"end":0.8,"curve":"Pulse"},"tone":{"start":0.88,"end":0.8,"curve":"Ease Out"},"vibrato":{"start":0.06535477262458739,"end":0.12,"curve":"Linear"},"level":{"start":0.8,"end":0.35,"curve":"Ease Out"},"attack":0.0026487940210504985,"release":0.06214902321741278,"resonance":0.28136260691298515,"echo":0,"waveTo":7,"morph":{"start":0.2,"end":0.2275813272908366,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.25,"pitch":{"start":0.6727141258149083,"end":0.8,"curve":"Pulse"},"tone":{"start":0.88,"end":0.628790327624828,"curve":"Ease Out"},"vibrato":{"start":0.0728488145721001,"end":0.03784173436044493,"curve":"Linear"},"level":{"start":0.6127263108376241,"end":0.22276145050568827,"curve":"Ease Out"},"attack":0.004094151291168701,"release":0.16,"resonance":0.1720670567359741,"echo":0,"waveTo":7,"morph":{"start":0.38,"end":0.2939591335719668,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09302961341975986,"pitch":{"start":0.7,"end":0.737576229983484,"curve":"Pulse"},"tone":{"start":0.7532509244402495,"end":0.6938840962709244,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7915135571804239,"end":0.29628994604055914,"curve":"Ease Out"},"attack":0.005960229507005098,"release":0.06310909772840147,"resonance":0.2333530156605204,"echo":0,"waveTo":7,"morph":{"start":0.34623766984509163,"end":0.3499868995350187,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.09755089911174004,"pitch":{"start":0.6799477816955549,"end":0.7580247415248396,"curve":"Pulse"},"tone":{"start":0.68,"end":0.7754422577089706,"curve":"Ease Out"},"vibrato":{"start":0.11444040100257669,"end":0,"curve":"Linear"},"level":{"start":0.6452967903791684,"end":0.236418177874905,"curve":"Ease Out"},"attack":0.004956076884294636,"release":0.06254011666898975,"resonance":0.12,"echo":0,"waveTo":7,"morph":{"start":0.2996816539688901,"end":0.37913088106338305,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.25,"pitch":{"start":0.68848635218355,"end":0.69,"curve":"Pulse"},"tone":{"start":0.8122632467009026,"end":0.7356341633524264,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7515593107247512,"end":0.23019178415647368,"curve":"Ease Out"},"attack":0.0032569528910388825,"release":0.16,"resonance":0.3117612063209213,"echo":0,"waveTo":7,"morph":{"start":0.38,"end":0.38,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.10194217388546652,"pitch":{"start":0.57,"end":0.7846454270258396,"curve":"Pulse"},"tone":{"start":0.8627765968650666,"end":0.6115296894332196,"curve":"Ease Out"},"vibrato":{"start":0.05034102951686751,"end":0.0030005760999617308,"curve":"Linear"},"level":{"start":0.7338756919489102,"end":0.15,"curve":"Ease Out"},"attack":0.001,"release":0.07041514371381269,"resonance":0.3307080253061011,"echo":0,"waveTo":7,"morph":{"start":0.2,"end":0.21023788994357584,"curve":"Linear"}}]},{"id":"bass_plucks","name":"Bass Plucks","tip":"Low rounded notes with a quick onset and a soft tail.","limits":{},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C073","C074","C075","C076","C077","C078","C079","C080","C081","C082","C083","C084","C085","C086","C087","C088","C089","C090","C091","C092","C093","C094","C095","C096"],"survey_source_ids":["T497","T422","T132","T010","T266","T051","T455","T131","T282","T327","T302","T314","T391","T143","T354","T465","T005","T392","T446","T434","T039","T145","T264","T401"],"exemplars":[{"masterVolume":0.5,"waveType":1,"duration":0.4120788427829672,"pitch":{"start":0.10794076802209021,"end":0,"curve":"Ease Out"},"tone":{"start":0.6251321899704635,"end":0,"curve":"Ease Out"},"vibrato":{"start":0.18472924071829766,"end":0.2881123122991994,"curve":"Ease In"},"level":{"start":0.9621668591862544,"end":0.07269942632410675,"curve":"Linear"},"attack":0.002841923053675636,"release":0.3552403817094545,"resonance":0.8238561326405033,"echo":0,"waveTo":7,"morph":{"start":0.050137439812533546,"end":0.45946268937550483,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.20280730680108855,"pitch":{"start":0.37972706617321816,"end":0.21465089024044573,"curve":"Ease In"},"tone":{"start":0.45720113102579485,"end":0.13116775254020469,"curve":"Triangle"},"vibrato":{"start":0.21713728760369122,"end":0.2247753175906837,"curve":"Ease In"},"level":{"start":0.8377973319380544,"end":0.5229524267744273,"curve":"Linear"},"attack":0.012530486877076327,"release":0.059146263308665875,"resonance":0.3622887239675037,"echo":0,"waveTo":7,"morph":{"start":0.011143111330457032,"end":0.1450015957094729,"curve":"Ease Out"}},{"masterVolume":0.5,"waveType":1,"duration":0.9950483611593516,"pitch":{"start":0.05852972069755197,"end":0.42568560814484946,"curve":"Linear"},"tone":{"start":0.33631566583644595,"end":0.8378049696912058,"curve":"Steps"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.41731892760144546,"end":0.35621896042488516,"curve":"Smooth"},"attack":0.013768043456599115,"release":0.3807303942680384,"resonance":0.7027211745269596,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.12927007377442482,"pitch":{"start":0.1511867910856381,"end":0.33261898406781254,"curve":"Ease Out"},"tone":{"start":0.8119421187439002,"end":0.8841049690381624,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Pulse"},"level":{"start":0.463699665130116,"end":0.8660048246383667,"curve":"Pulse"},"attack":0.03329462224136175,"release":0.053218956431781365,"resonance":0.3265049200505018,"echo":0.2119593240669928,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.1175579989407977,"pitch":{"start":0.2293597019277513,"end":0.1744898402877152,"curve":"Ease Out"},"tone":{"start":0.4858873059274628,"end":0.6297750854748302,"curve":"Ease In"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7590243122307583,"end":0.7047163669485599,"curve":"Bounce"},"attack":0.008065038217697293,"release":0.03605164353330277,"resonance":0.7118115853867494,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.42915902886090573,"pitch":{"start":0.26591257024090736,"end":0.2758031813893467,"curve":"Triangle"},"tone":{"start":0.8879014742095024,"end":0.10703813239233569,"curve":"Steps"},"vibrato":{"start":0.938939816551283,"end":0.6104695724789053,"curve":"Linear"},"level":{"start":0.4575492100906558,"end":0.9308017630595714,"curve":"Triangle"},"attack":0.09802051061616593,"release":0.2029506583993086,"resonance":0.18831449314020574,"echo":0,"waveTo":7,"morph":{"start":0.19874615837819876,"end":0.10142528595868498,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":2,"duration":0.20867281117273873,"pitch":{"start":0.749059372083284,"end":0.2882680290006101,"curve":"Ease In"},"tone":{"start":0.09459373039426282,"end":0.06105210545938462,"curve":"Ease In"},"vibrato":{"start":0,"end":0,"curve":"Triangle"},"level":{"start":0.9889064905350097,"end":0.47126590198837226,"curve":"Triangle"},"attack":0.014442634580656885,"release":0.09067372507414068,"resonance":0.1685024786973372,"echo":0,"waveTo":7,"morph":{"start":0.8612171094864607,"end":0.9979773529339582,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":1,"duration":0.6108935378555341,"pitch":{"start":0.23763854276854546,"end":0.46940499264746904,"curve":"Linear"},"tone":{"start":0.4952368084224872,"end":0.8938159675337374,"curve":"Pulse"},"vibrato":{"start":0.21442164247855544,"end":0,"curve":"Steps"},"level":{"start":0.7829525439883582,"end":0.14538841960020366,"curve":"Bounce"},"attack":0.010808986240066588,"release":0.3793319036925011,"resonance":0.853327833674848,"echo":0.5187207964481786,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.16874078172340035,"pitch":{"start":0.03469696948304772,"end":0.10734794152900576,"curve":"Bounce"},"tone":{"start":0.507778501114808,"end":0.8722680770908482,"curve":"Ease In"},"vibrato":{"start":0.3030078914016485,"end":0.20714626950211823,"curve":"Triangle"},"level":{"start":0.7357693068683147,"end":0.6595161151792854,"curve":"Smooth"},"attack":0.06208866060067152,"release":0.08013496526979692,"resonance":0.49243065862683577,"echo":0.5746709881117568,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.3209569213739586,"pitch":{"start":0.11116505828686059,"end":0.41703875383362166,"curve":"Ease In"},"tone":{"start":0.33802721766987814,"end":0.2674924322636798,"curve":"Triangle"},"vibrato":{"start":0,"end":0,"curve":"Ease In"},"level":{"start":0.8507750460878014,"end":0.6146969067491591,"curve":"Linear"},"attack":0.010138447623699903,"release":0.0988527553215355,"resonance":0.7812467096606269,"echo":0,"waveTo":7,"morph":{"start":0.6243208460509777,"end":0.4851925193797797,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":1,"duration":1.3715181554833948,"pitch":{"start":0.3189439279586077,"end":0.29656629683449864,"curve":"Smooth"},"tone":{"start":0.2065101808286272,"end":0.6899825236178003,"curve":"Triangle"},"vibrato":{"start":0,"end":0.2597481096163392,"curve":"Linear"},"level":{"start":0.7327636083122342,"end":0.46955391696654264,"curve":"Linear"},"attack":0.014628673817496746,"release":0.8150557903182772,"resonance":0.09491072219097986,"echo":0,"waveTo":7,"morph":{"start":0.12396336807403714,"end":0.10112812244798988,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":1,"duration":0.17348819106517502,"pitch":{"start":0.3182975154672749,"end":0.31821478353813293,"curve":"Bounce"},"tone":{"start":0.4778757872059941,"end":0.11976156025193632,"curve":"Ease Out"},"vibrato":{"start":0.7145260404795408,"end":0,"curve":"Ease Out"},"level":{"start":0.4100792572251521,"end":0.2901862109731883,"curve":"Pulse"},"attack":0.07688517445099878,"release":0.10227243139553212,"resonance":0.2662339320639148,"echo":0.6403786487877369,"waveTo":7,"morph":{"start":0.1399253590637818,"end":0.025942958453670145,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.09398306447067517,"pitch":{"start":0.17039841815130785,"end":0.25457252009771764,"curve":"Ease In"},"tone":{"start":0.2905246839043684,"end":0.5448536851443351,"curve":"Ease In"},"vibrato":{"start":0.31484516244381666,"end":0,"curve":"Linear"},"level":{"start":0.8705310855526477,"end":0.5277125895023346,"curve":"Bounce"},"attack":0.0033000603206455705,"release":0.018163812187487416,"resonance":0.12229650927474722,"echo":0.3766536614741198,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.42500191221089245,"pitch":{"start":0.24981740838848054,"end":0.3446647028345614,"curve":"Smooth"},"tone":{"start":0.31783993997378274,"end":0.4348493402590975,"curve":"Steps"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.4153131862170994,"end":0.12675389469601214,"curve":"Triangle"},"attack":0.07383134681646716,"release":0.2935519582790063,"resonance":0.08132943890523166,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.5714874132945608,"pitch":{"start":0.24767420490039513,"end":0.43136965475976463,"curve":"Linear"},"tone":{"start":0.09565966438967735,"end":0.19786683120764792,"curve":"Triangle"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.9553040858940222,"end":0.46899167808704084,"curve":"Steps"},"attack":0.2200938161292644,"release":0.29091394116067404,"resonance":0.1933150020893663,"echo":0,"waveTo":7,"morph":{"start":0.9447258370928466,"end":0.7822099854936823,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.615018474334676,"pitch":{"start":0.15189153705723585,"end":0,"curve":"Triangle"},"tone":{"start":0.7159089624416083,"end":0.2678466330235824,"curve":"Ease Out"},"vibrato":{"start":0,"end":0.11020265482366084,"curve":"Ease In"},"level":{"start":1,"end":0.1553478791611269,"curve":"Pulse"},"attack":0.00424150671954949,"release":0.5301883399436863,"resonance":0.16418081369483842,"echo":0,"waveTo":7,"morph":{"start":0.2067602513823658,"end":0.520561378239654,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.5392421240076711,"pitch":{"start":0.1716192879155278,"end":0.5616192879155278,"curve":"Ease In"},"tone":{"start":0.7795508011244238,"end":0.8240367119200528,"curve":"Linear"},"vibrato":{"start":0.008080054656602442,"end":0.16928282505832612,"curve":"Ease In"},"level":{"start":0.7483520643319934,"end":0.0018439762294292505,"curve":"Linear"},"attack":0.004257174663218457,"release":0.36895513747893294,"resonance":0.06144240634748712,"echo":0.19970892509212718,"waveTo":7,"morph":{"start":0.13296345947310328,"end":0.05146382108796388,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":0,"duration":0.16458648579071336,"pitch":{"start":0.0959666453814134,"end":0.2819502892717719,"curve":"Ease In"},"tone":{"start":0.4532418074435554,"end":0.28663546598982065,"curve":"Ease In"},"vibrato":{"start":0,"end":0.7525457125157118,"curve":"Ease Out"},"level":{"start":0.5293024115264415,"end":0.45065701848827305,"curve":"Bounce"},"attack":0.002504504084587097,"release":0.014625178643959378,"resonance":0.3703929377370514,"echo":0.488902608025819,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":1.6527113518084178,"pitch":{"start":0.12942780244862662,"end":0.11205492356792092,"curve":"Steps"},"tone":{"start":0.6886229902738705,"end":0.15037065331125632,"curve":"Pulse"},"vibrato":{"start":0.38686280720867217,"end":0,"curve":"Ease Out"},"level":{"start":0.3956557625671848,"end":0.516645058169961,"curve":"Linear"},"attack":0.005316106336656958,"release":0.9946046925675995,"resonance":0.5224336946266703,"echo":0.37255515537690365,"waveTo":7,"morph":{"start":0.08885095974896103,"end":0.19667804833035915,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.18442445236841232,"pitch":{"start":0.04968858252279461,"end":0.10340158915147185,"curve":"Triangle"},"tone":{"start":0.354185339063406,"end":0.6825472454424016,"curve":"Smooth"},"vibrato":{"start":0.35940239182673395,"end":0.35346668935380876,"curve":"Steps"},"level":{"start":0.915036991785746,"end":0.4403233605716378,"curve":"Smooth"},"attack":0.002796387962065637,"release":0.10460052650538641,"resonance":0.05026997849345207,"echo":0.13025130954338238,"waveTo":7,"morph":{"start":0.11900003121700138,"end":0.14157171924132853,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":2,"duration":0.09348989977268601,"pitch":{"start":0.17962729528779164,"end":0.22232859032228589,"curve":"Ease In"},"tone":{"start":0.2143067389028147,"end":0.0781422907835804,"curve":"Steps"},"vibrato":{"start":0.8646741260308772,"end":0,"curve":"Steps"},"level":{"start":0.5128889700747095,"end":0.22160264410078528,"curve":"Triangle"},"attack":0.03817168835033135,"release":0.014388415495875556,"resonance":0.36633960457984355,"echo":0.5140646667685359,"waveTo":7,"morph":{"start":0.1181061175931245,"end":0.05665811005979776,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":1,"duration":0.5831549860097335,"pitch":{"start":0.2117315272241831,"end":0,"curve":"Linear"},"tone":{"start":0.44689072147011755,"end":0,"curve":"Ease Out"},"vibrato":{"start":0.1079206980066374,"end":0.19407604783773422,"curve":"Ease In"},"level":{"start":0.7654042054200545,"end":0,"curve":"Ease Out"},"attack":0.004021758524205059,"release":0.5027198155256324,"resonance":0.25481069716624916,"echo":0,"waveTo":7,"morph":{"start":0.23642262881621717,"end":0.6468594214180484,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.8043393319960089,"pitch":{"start":0.23377747686579822,"end":0.5452752836141735,"curve":"Ease In"},"tone":{"start":0.11949423440964893,"end":0.8090267801191657,"curve":"Steps"},"vibrato":{"start":0.17948707658797503,"end":0.5151974081527442,"curve":"Bounce"},"level":{"start":0.3561349065275863,"end":0.12068815698847174,"curve":"Smooth"},"attack":0.010158402311615645,"release":0.6430045109341052,"resonance":0.22620891695842146,"echo":0.4631798698450438,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.40400360111091943,"pitch":{"start":0.17412671216763556,"end":0,"curve":"Ease In"},"tone":{"start":0.364439616817981,"end":0,"curve":"Ease Out"},"vibrato":{"start":0.08817241690121591,"end":0.22298813178204,"curve":"Ease In"},"level":{"start":1,"end":0.22913656092714518,"curve":"Linear"},"attack":0.0027862317317994445,"release":0.34827896647493056,"resonance":0.044760653504636136,"echo":0,"waveTo":7,"morph":{"start":0.5353917689761147,"end":0.4439302548067644,"curve":"Linear"}}]},{"id":"soft_pips","name":"Soft Pips","tip":"Gentle, clean sine pips with a cushioned onset and almost no pitch motion.","limits":{"waveTo":-1,"waveType":0,"duration":[0.1,0.19],"attack":[0.014,0.028],"release":[0.06,0.14],"echo":0,"resonance":[0,0.1],"pitch.start":[0.42,0.55],"pitch.end":[0.395,0.565],"pitch.curve":"Ease Out","tone.start":[0.48,0.62],"tone.end":[0.43,0.58],"tone.curve":"Smooth","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.38,0.55],"level.end":[0.18,0.35],"level.curve":"Smooth"},"intervals":{"pitch":[-0.025,0.015]},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C097","C098","C099","C100","C101","C102","C103","C104","C105","C106","C107","C108"],"survey_source_ids":["T342","T086","T064","T278","T495","T315","T279","T498","T459","T439","T231","T306"],"exemplars":[{"masterVolume":0.5,"waveType":0,"duration":0.11046274681848725,"pitch":{"start":0.4352347989204401,"end":0.4502347989204401,"curve":"Ease Out"},"tone":{"start":0.5530753234586144,"end":0.4458706855664352,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.3387856614705695,"curve":"Smooth"},"attack":0.014,"release":0.06133736909345538,"resonance":0.1,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.10618423022252484,"pitch":{"start":0.42,"end":0.435,"curve":"Ease Out"},"tone":{"start":0.48,"end":0.5448354513473713,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5132847216684965,"end":0.2070133454336179,"curve":"Smooth"},"attack":0.01579710241772847,"release":0.06,"resonance":0.08796609616790708,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.1,"pitch":{"start":0.47865311904567914,"end":0.49365311904567916,"curve":"Ease Out"},"tone":{"start":0.6109087496093168,"end":0.4554776719953875,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.38,"end":0.29017517634272094,"curve":"Smooth"},"attack":0.014855803692615834,"release":0.07976013505530329,"resonance":0.05883958961861531,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.1552512325600194,"pitch":{"start":0.5268775748192862,"end":0.5018775748192862,"curve":"Ease Out"},"tone":{"start":0.62,"end":0.4988461406430124,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.38,"end":0.20605545929566438,"curve":"Smooth"},"attack":0.023834453503515873,"release":0.14,"resonance":0.1,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.10984315792349766,"pitch":{"start":0.4322108068664109,"end":0.4472108068664109,"curve":"Ease Out"},"tone":{"start":0.5071301292148478,"end":0.43,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5106506820821283,"end":0.35,"curve":"Smooth"},"attack":0.023428675751886813,"release":0.08573312691405706,"resonance":0.04138562246684643,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.18180502195595,"pitch":{"start":0.4533966916853688,"end":0.4683966916853688,"curve":"Ease Out"},"tone":{"start":0.5142595599415528,"end":0.43,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.4578244206545981,"end":0.3215655716456284,"curve":"Smooth"},"attack":0.014,"release":0.10212681303076024,"resonance":0.033440378540746545,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.11275883432605532,"pitch":{"start":0.4463058700064867,"end":0.4463714529490905,"curve":"Ease Out"},"tone":{"start":0.48,"end":0.58,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.43554523375194076,"end":0.35,"curve":"Smooth"},"attack":0.01420190593451409,"release":0.061942961986373356,"resonance":0,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.19,"pitch":{"start":0.5098901806259957,"end":0.48489018062599565,"curve":"Ease Out"},"tone":{"start":0.5606979810406891,"end":0.45402389120658243,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.392646501191484,"end":0.23930887918792546,"curve":"Smooth"},"attack":0.028,"release":0.14,"resonance":0.031938758455536696,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.14351482985300962,"pitch":{"start":0.4376432445764096,"end":0.4526432445764096,"curve":"Ease Out"},"tone":{"start":0.5865695509979176,"end":0.58,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.3932445573571892,"end":0.18,"curve":"Smooth"},"attack":0.028,"release":0.13633529735015842,"resonance":0.0029900681000119955,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.14609290256741134,"pitch":{"start":0.55,"end":0.525,"curve":"Ease Out"},"tone":{"start":0.6109197587333248,"end":0.4753021020060928,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.4544542675436348,"end":0.18,"curve":"Smooth"},"attack":0.015162137621526503,"release":0.13946720694224737,"resonance":0.07832455313451293,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.1,"pitch":{"start":0.55,"end":0.565,"curve":"Ease Out"},"tone":{"start":0.5155510945093723,"end":0.44322971019080537,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.2613720265038593,"curve":"Smooth"},"attack":0.01972061426377041,"release":0.06,"resonance":0.08537089673129916,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.19,"pitch":{"start":0.42,"end":0.435,"curve":"Ease Out"},"tone":{"start":0.62,"end":0.5470033179070233,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.41119753030231193,"end":0.18144039119353797,"curve":"Smooth"},"attack":0.01486140392674851,"release":0.08248132574673353,"resonance":0,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}}]},{"id":"sand_sprays","name":"Sand Sprays","tip":"A short bright powdery spray: all grain, with no pitched note.","limits":{"waveTo":7,"waveType":0,"duration":[0.14,0.42],"attack":[0.001,0.01],"release":[0.08,0.2],"echo":0,"resonance":[0,0.15],"pitch.start":[0.3,0.45],"pitch.end":[0.3,0.45],"pitch.curve":"Linear","tone.start":[0.64,0.8],"tone.end":[0.63,0.79],"tone.curve":"Linear","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.65,0.9],"level.end":[0.2,0.45],"level.curve":"Ease Out","morph.start":1,"morph.end":1,"morph.curve":"Linear"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C109","C110","C111","C112","C113","C114","C115","C116","C117","C118","C119","C120"],"survey_source_ids":["T479","T254","T510","T376","T116","T360","T492","T102","T126","T226","T230","T379"],"exemplars":[{"masterVolume":0.5,"waveType":0,"duration":0.42,"pitch":{"start":0.45,"end":0.3926628474843703,"curve":"Linear"},"tone":{"start":0.6687563382779743,"end":0.6821113192307758,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7811767772699219,"end":0.4394348099475499,"curve":"Ease Out"},"attack":0.0013322972885761847,"release":0.2,"resonance":0.027956249982453087,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.3360696293891601,"pitch":{"start":0.34124737845763287,"end":0.3,"curve":"Linear"},"tone":{"start":0.8,"end":0.655402636616535,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7437120338396676,"end":0.45,"curve":"Ease Out"},"attack":0.003024278288591172,"release":0.2,"resonance":0,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.2763944715422961,"pitch":{"start":0.32096281449779773,"end":0.45,"curve":"Linear"},"tone":{"start":0.7901540495988696,"end":0.63,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8826295260511133,"end":0.23870042589419874,"curve":"Ease Out"},"attack":0.01,"release":0.13336432874439832,"resonance":0.13492932467352298,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.2220189662242355,"pitch":{"start":0.3,"end":0.41040910729295743,"curve":"Linear"},"tone":{"start":0.7959191835770743,"end":0.7158382942115221,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.65,"end":0.296529580347268,"curve":"Ease Out"},"attack":0.0019245250242448013,"release":0.16167801452183964,"resonance":0.04810617905146953,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.17905019922044765,"pitch":{"start":0.326926127768552,"end":0.3,"curve":"Linear"},"tone":{"start":0.7223598306690869,"end":0.7148192286676583,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8310003953345957,"end":0.2,"curve":"Ease Out"},"attack":0.001677751641146143,"release":0.14826667796914272,"resonance":0.15,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.26814904290835784,"pitch":{"start":0.3,"end":0.31459571581306295,"curve":"Linear"},"tone":{"start":0.6895229266027967,"end":0.79,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.65,"end":0.26359911160785765,"curve":"Ease Out"},"attack":0.002832765123362676,"release":0.1487639897888805,"resonance":0.013038863157429336,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.23328567550313167,"pitch":{"start":0.4046728616060098,"end":0.3843855186897219,"curve":"Linear"},"tone":{"start":0.6874715621981914,"end":0.79,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9,"end":0.2976332799401144,"curve":"Ease Out"},"attack":0.004071470885181555,"release":0.17239300946794622,"resonance":0,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.42,"pitch":{"start":0.3154988235194126,"end":0.3021111607574198,"curve":"Linear"},"tone":{"start":0.8,"end":0.63,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7224668314358307,"end":0.2,"curve":"Ease Out"},"attack":0.001,"release":0.12156324362059728,"resonance":0.033176921088276426,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.15068692466991085,"pitch":{"start":0.35015935736488346,"end":0.3977257488222091,"curve":"Linear"},"tone":{"start":0.7009630491113724,"end":0.7654827393425387,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.6976298994787264,"end":0.45,"curve":"Ease Out"},"attack":0.002865088036111658,"release":0.11213991667289538,"resonance":0.025492993294905706,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.14,"pitch":{"start":0.43580328740013474,"end":0.41863897107795556,"curve":"Linear"},"tone":{"start":0.64,"end":0.720227191260197,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9,"end":0.3362780430989014,"curve":"Ease Out"},"attack":0.001,"release":0.08,"resonance":0.15,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.14,"pitch":{"start":0.32268311268901867,"end":0.43037974818482383,"curve":"Linear"},"tone":{"start":0.7153823127391384,"end":0.705246874377708,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8217827553759491,"end":0.42714201323207523,"curve":"Ease Out"},"attack":0.002314253364504675,"release":0.08,"resonance":0.14194284356395,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.17922548918235442,"pitch":{"start":0.45,"end":0.45,"curve":"Linear"},"tone":{"start":0.64,"end":0.7488267624346155,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.875068981433961,"end":0.3812822768437187,"curve":"Ease Out"},"attack":0.01,"release":0.08632224062102065,"resonance":0.028658291714924546,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}}]},{"id":"air_currents","name":"Air Currents","tip":"A longer, dark breath of air that eases in and out smoothly.","limits":{"waveTo":7,"waveType":0,"duration":[0.9,1.65],"attack":[0.2,0.45],"release":[0.35,0.65],"echo":0,"resonance":[0.05,0.22],"pitch.start":[0.25,0.4],"pitch.end":[0.25,0.4],"pitch.curve":"Linear","tone.start":[0.32,0.47],"tone.end":[0.31,0.46],"tone.curve":"Smooth","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.55,0.8],"level.end":[0.4,0.65],"level.curve":"Smooth","morph.start":1,"morph.end":1,"morph.curve":"Linear"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C121","C122","C123","C124","C125","C126","C127","C128","C129","C130","C131","C132"],"survey_source_ids":["T452","T096","T317","T093","T061","T125","T445","T464","T381","T253","T343","T413"],"exemplars":[{"masterVolume":0.5,"waveType":0,"duration":1.330919099593035,"pitch":{"start":0.3445085076816377,"end":0.39087458922395385,"curve":"Linear"},"tone":{"start":0.47,"end":0.3730976748046064,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.4,"curve":"Smooth"},"attack":0.3967872269557468,"release":0.6338120397941123,"resonance":0.21999999999999997,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.4138980375813945,"pitch":{"start":0.4,"end":0.2755412703868273,"curve":"Linear"},"tone":{"start":0.43284205333085807,"end":0.443326173661627,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5846220989233005,"end":0.4,"curve":"Smooth"},"attack":0.2,"release":0.65,"resonance":0.08681632430512853,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.6117874190235608,"pitch":{"start":0.25,"end":0.25,"curve":"Linear"},"tone":{"start":0.38573473651467405,"end":0.31,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8,"end":0.65,"curve":"Smooth"},"attack":0.4101827151204077,"release":0.5835041105033855,"resonance":0.11564714133430926,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.9325583028478012,"pitch":{"start":0.4,"end":0.28495219545523,"curve":"Linear"},"tone":{"start":0.32,"end":0.38445028510599366,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7352135587568654,"end":0.65,"curve":"Smooth"},"attack":0.26903563869708796,"release":0.3606808540623053,"resonance":0.05,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.9,"pitch":{"start":0.26139153026073286,"end":0.25,"curve":"Linear"},"tone":{"start":0.33867171023416304,"end":0.4154585306946554,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.6735315542913017,"end":0.65,"curve":"Smooth"},"attack":0.2622698491184986,"release":0.35,"resonance":0.1443764200571379,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.65,"pitch":{"start":0.25,"end":0.25,"curve":"Linear"},"tone":{"start":0.3342918811280571,"end":0.4043331113079629,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.6658318113922858,"end":0.65,"curve":"Smooth"},"attack":0.45,"release":0.65,"resonance":0.16070138326176292,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.130037462007685,"pitch":{"start":0.25,"end":0.25,"curve":"Linear"},"tone":{"start":0.3947100651057655,"end":0.3731148846000016,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7818274493295394,"end":0.65,"curve":"Smooth"},"attack":0.3100727575516048,"release":0.42546451582727796,"resonance":0.09322419300603395,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.413879925890341,"pitch":{"start":0.33359089429223676,"end":0.4,"curve":"Linear"},"tone":{"start":0.47,"end":0.36926417780939974,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7438609869555058,"end":0.5502348046301981,"curve":"Smooth"},"attack":0.45,"release":0.43059163060180233,"resonance":0.2064656030670165,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.65,"pitch":{"start":0.28511189132087095,"end":0.25,"curve":"Linear"},"tone":{"start":0.32,"end":0.46,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.4579550811586723,"curve":"Smooth"},"attack":0.4190057796455125,"release":0.5974327303451267,"resonance":0.15160379527041973,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":1.1664234695242426,"pitch":{"start":0.25,"end":0.25,"curve":"Linear"},"tone":{"start":0.39442835710714286,"end":0.31,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.6401289232226774,"end":0.5542683693583155,"curve":"Smooth"},"attack":0.3176339448761335,"release":0.43740106049335054,"resonance":0.21999999999999997,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.9,"pitch":{"start":0.278490525718813,"end":0.4,"curve":"Linear"},"tone":{"start":0.3957085342423711,"end":0.46,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5629558179389372,"end":0.6309279043409395,"curve":"Smooth"},"attack":0.2,"release":0.35,"resonance":0.05,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.9000007661428129,"pitch":{"start":0.25,"end":0.25,"curve":"Linear"},"tone":{"start":0.3642383008121085,"end":0.3341570949666742,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8,"end":0.65,"curve":"Smooth"},"attack":0.2622700260164547,"release":0.35000025133556906,"resonance":0.2182876533611296,"echo":0,"waveTo":7,"morph":{"start":1,"end":1,"curve":"Linear"}}]},{"id":"submarine_calls","name":"Mournful Calls","tip":"Low, woozy electronic calls with a plaintive, fading voice.","limits":{},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C133","C134","C135","C136","C137","C138","C139","C140","C141","C142","C143","C144","C145","C146","C147","C148","C149","C150","C151","C152","C153","C154","C155","C156"],"survey_source_ids":["T274","T025","T462","T103","T294","T209","T426","T299","T427","T090","T219","T295","T438","T211","T043","T176","T046","T050","T185","T344","T305","T369","T506","T049"],"exemplars":[{"masterVolume":0.5,"waveType":3,"duration":0.7598611296943839,"pitch":{"start":0.32998165784636513,"end":0.27811750474385916,"curve":"Triangle"},"tone":{"start":0.47975030232919375,"end":0.2581427636556327,"curve":"Steps"},"vibrato":{"start":0.2546772169880569,"end":0.6602937446441501,"curve":"Triangle"},"level":{"start":0.6010185234830714,"end":0.38325059554539626,"curve":"Bounce"},"attack":0.017406939547508955,"release":0.4569814740215031,"resonance":0.5108267292031087,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":2.0682104594849426,"pitch":{"start":0.4544504626747221,"end":0.18445046267472207,"curve":"Smooth"},"tone":{"start":0.8153671115869656,"end":0.39514590783510356,"curve":"Smooth"},"vibrato":{"start":0.993391124624759,"end":0,"curve":"Pulse"},"level":{"start":0.989525900920853,"end":0.3460862251278013,"curve":"Ease Out"},"attack":0.31379744902530166,"release":0.7844936225632542,"resonance":0.09963539628079161,"echo":0.09345439001219347,"waveTo":7,"morph":{"start":0,"end":0.3060806991765276,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":3,"duration":0.6153489957174351,"pitch":{"start":0.10059529858175666,"end":0.06104127584025264,"curve":"Smooth"},"tone":{"start":0.8892524504102767,"end":0.9895044129807502,"curve":"Bounce"},"vibrato":{"start":0.22925429604947567,"end":0,"curve":"Linear"},"level":{"start":0.7548348576528952,"end":0.7330736475531011,"curve":"Ease In"},"attack":0.20806825299428022,"release":0.28204868454673193,"resonance":0.6342744884314016,"echo":0,"waveTo":7,"morph":{"start":0.31634328165091574,"end":0.23812404577620327,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.3037788452715555,"pitch":{"start":0.4106644804752432,"end":0.48399856467731295,"curve":"Ease In"},"tone":{"start":0.14112126720137894,"end":0.10932949277339503,"curve":"Ease Out"},"vibrato":{"start":0,"end":0.743443843908608,"curve":"Pulse"},"level":{"start":0.5691890705260448,"end":0.2347099631279707,"curve":"Smooth"},"attack":0.01265828549908474,"release":0.1237823136153787,"resonance":0.6430196126922965,"echo":0.17641566852107643,"waveTo":7,"morph":{"start":0.7939341854769736,"end":0.9827716861153022,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":1,"duration":2.3055068195192723,"pitch":{"start":0.3558962672576308,"end":0.26170920936390757,"curve":"Ease In"},"tone":{"start":0.9523214165121316,"end":0.41035736633930353,"curve":"Bounce"},"vibrato":{"start":0,"end":0.38313514506444335,"curve":"Ease Out"},"level":{"start":0.4308770200470462,"end":0.4636685929540545,"curve":"Bounce"},"attack":0.20398833125339247,"release":0.5314931634550265,"resonance":0.8861180566367692,"echo":0.288300219271332,"waveTo":7,"morph":{"start":0.06697419949341565,"end":0.043616433343850076,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.6662466121597359,"pitch":{"start":0.22577125795185565,"end":0,"curve":"Ease Out"},"tone":{"start":0.6971976455766707,"end":0,"curve":"Ease Out"},"vibrato":{"start":0,"end":0.17365437848493456,"curve":"Smooth"},"level":{"start":1,"end":0.23799626471009105,"curve":"Smooth"},"attack":0.0045948042217912825,"release":0.5743505277239103,"resonance":0.5916964659350924,"echo":0,"waveTo":7,"morph":{"start":0.3022626694990322,"end":0.7159640128025785,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.6277922127766334,"pitch":{"start":0.42904157065087933,"end":0.43499720832332966,"curve":"Ease Out"},"tone":{"start":0.9325358573929406,"end":0.7706190325552598,"curve":"Bounce"},"vibrato":{"start":0,"end":0.4356173339765519,"curve":"Steps"},"level":{"start":0.7074148207786493,"end":0.9002223187405616,"curve":"Smooth"},"attack":0.07137425559228347,"release":0.16817470045632635,"resonance":0.21370253135683015,"echo":0.3740431713755242,"waveTo":7,"morph":{"start":0.14294013503938913,"end":0.10250376644078642,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":0,"duration":1.5022848668754976,"pitch":{"start":0.1635790005605668,"end":0.45022940851747983,"curve":"Ease Out"},"tone":{"start":0.7552036091219634,"end":0.27526232466334477,"curve":"Triangle"},"vibrato":{"start":0,"end":0.3448047894053161,"curve":"Pulse"},"level":{"start":0.8004117842298001,"end":0.1539677218347788,"curve":"Steps"},"attack":0.0038774752635508773,"release":0.15166145269411235,"resonance":0.25887008138233797,"echo":0.6532082495861686,"waveTo":7,"morph":{"start":0.1271157799148932,"end":0.0026662773406133057,"curve":"Steps"}},{"masterVolume":0.5,"waveType":2,"duration":0.1089356082077042,"pitch":{"start":0.08810193032724783,"end":0.0960967028979212,"curve":"Ease Out"},"tone":{"start":0.5356850363779813,"end":0.643397492240183,"curve":"Triangle"},"vibrato":{"start":0.8976480083074421,"end":0,"curve":"Triangle"},"level":{"start":0.6000788141274824,"end":0.22887368801981212,"curve":"Smooth"},"attack":0.00720186971174553,"release":0.07579355071192385,"resonance":0.32335281728301196,"echo":0.24274993411963802,"waveTo":7,"morph":{"start":0.1753091333853081,"end":0.19090257551986725,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":1,"duration":1.0513758110037266,"pitch":{"start":0.5234163537598215,"end":0.4860124433040619,"curve":"Bounce"},"tone":{"start":0.6620422536972911,"end":0.4508165710256435,"curve":"Ease In"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.6287104904768057,"end":0.6793432714045048,"curve":"Triangle"},"attack":0.01710406751045957,"release":0.1323689751055792,"resonance":0.02751773236086592,"echo":0,"waveTo":7,"morph":{"start":0.08161299559287727,"end":0.5348474476486444,"curve":"Steps"}},{"masterVolume":0.5,"waveType":2,"duration":0.5149258415568502,"pitch":{"start":0.5525115161715075,"end":0.4604436422418803,"curve":"Bounce"},"tone":{"start":0.32516852382104844,"end":0.1354616381460801,"curve":"Triangle"},"vibrato":{"start":0.04746692255139351,"end":0,"curve":"Smooth"},"level":{"start":0.6321295894565993,"end":0.18679584299214186,"curve":"Pulse"},"attack":0.013808676136191933,"release":0.0946869234991121,"resonance":0.756774451653473,"echo":0.5566502826754004,"waveTo":7,"morph":{"start":0.785342525690794,"end":0.4657290708273649,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":2,"duration":0.178256483967186,"pitch":{"start":0.17703481004806235,"end":0.1150799991376698,"curve":"Ease In"},"tone":{"start":0.5656505230930634,"end":0.5887629526900128,"curve":"Bounce"},"vibrato":{"start":0,"end":0,"curve":"Bounce"},"level":{"start":0.5955159917124547,"end":0.5393764042574912,"curve":"Bounce"},"attack":0.0036234390358440573,"release":0.11198934484871491,"resonance":0.9399156274273991,"echo":0,"waveTo":7,"morph":{"start":0.06569596783723682,"end":0.018829300277866425,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.5914968871054745,"pitch":{"start":0.28447443726472554,"end":0.08571124762296675,"curve":"Pulse"},"tone":{"start":0.6826615028898232,"end":0.7941862026345916,"curve":"Bounce"},"vibrato":{"start":0.16395509312860668,"end":0,"curve":"Smooth"},"level":{"start":0.4505770999123342,"end":0.5384436619561166,"curve":"Triangle"},"attack":0.18234414639596572,"release":0.14485227773100487,"resonance":0.2641561892698519,"echo":0.6040981156984344,"waveTo":7,"morph":{"start":0.17111726679839193,"end":0.15802490999456495,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":0,"duration":1.0242831311258433,"pitch":{"start":0.5063922899868339,"end":0.5949536685179919,"curve":"Triangle"},"tone":{"start":0.5013031566981226,"end":0.4960174350067973,"curve":"Smooth"},"vibrato":{"start":0,"end":0.39947259495966136,"curve":"Pulse"},"level":{"start":0.6388479632791131,"end":0.2676911665964872,"curve":"Linear"},"attack":0.004724951861891895,"release":0.15103345808372126,"resonance":0.032465196843259034,"echo":0,"waveTo":7,"morph":{"start":0.6281687812879682,"end":0.802343602059409,"curve":"Steps"}},{"masterVolume":0.5,"waveType":2,"duration":0.4238056597353029,"pitch":{"start":0.4723633210198023,"end":0.449510690048337,"curve":"Ease Out"},"tone":{"start":0.5316864523920231,"end":0.36616312272381035,"curve":"Pulse"},"vibrato":{"start":0,"end":0.2189541757106781,"curve":"Pulse"},"level":{"start":0.3578804190736264,"end":0.7463145899400115,"curve":"Smooth"},"attack":0.04594313213907477,"release":0.33730329524718994,"resonance":0.3074220537440851,"echo":0,"waveTo":7,"morph":{"start":0.19310026061255484,"end":0.18858876985497772,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":2,"duration":1.0025505933049355,"pitch":{"start":0.1813356747315265,"end":0.219473545756191,"curve":"Smooth"},"tone":{"start":0.3418872116366401,"end":0.2098473350517452,"curve":"Bounce"},"vibrato":{"start":0.035255267983302474,"end":0,"curve":"Ease Out"},"level":{"start":0.7020044815028086,"end":0.2779851457569748,"curve":"Steps"},"attack":0.0032063898537307975,"release":0.41232604791661526,"resonance":0.46928999600932,"echo":0,"waveTo":7,"morph":{"start":0.21095397552475334,"end":0.17942604045849295,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":2,"duration":1.2997822637657193,"pitch":{"start":0.2820505384448916,"end":0.1488209960144013,"curve":"Smooth"},"tone":{"start":0.2543921879609115,"end":0.42560618172865355,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9379359111189842,"end":0.8936048015300184,"curve":"Ease Out"},"attack":0.014955004043877123,"release":0.30704311982617993,"resonance":0.41174954071175307,"echo":0,"waveTo":7,"morph":{"start":0.08742646360304207,"end":0.0006790970731526614,"curve":"Ease Out"}},{"masterVolume":0.5,"waveType":0,"duration":0.2753838326426281,"pitch":{"start":0.3621005526906811,"end":0.15394376938231288,"curve":"Triangle"},"tone":{"start":0.8608282030094415,"end":0.23201919776620344,"curve":"Bounce"},"vibrato":{"start":0,"end":0.42345311772078276,"curve":"Ease Out"},"level":{"start":0.9336669519310817,"end":0.7485091500170529,"curve":"Ease In"},"attack":0.01765965053765103,"release":0.14608500969493007,"resonance":0.23010459624929352,"echo":0.20025397939607498,"waveTo":7,"morph":{"start":0.21950032256543636,"end":0.046915288339369,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.8313351689217904,"pitch":{"start":0.4737151441909373,"end":0.20371514419093728,"curve":"Smooth"},"tone":{"start":0.856444206670858,"end":0.1928547496907413,"curve":"Pulse"},"vibrato":{"start":0.9637074926635251,"end":0.04991973151918501,"curve":"Ease In"},"level":{"start":0.6609878813615069,"end":0.3680708311777562,"curve":"Linear"},"attack":0.1261336118364096,"release":0.31533402959102397,"resonance":0.8235977160278708,"echo":0.28468597956700253,"waveTo":7,"morph":{"start":0.17462925286963582,"end":0.20164653481915595,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.1596867888246958,"pitch":{"start":0.32027060966938736,"end":0.3550100580137223,"curve":"Pulse"},"tone":{"start":0.4293267624103464,"end":0.05234187577152625,"curve":"Smooth"},"vibrato":{"start":0,"end":0.12597306934185326,"curve":"Steps"},"level":{"start":0.6445106272120029,"end":0.2681996445078403,"curve":"Ease In"},"attack":0.013494312845170497,"release":0.11522377960991735,"resonance":0.37520907605066894,"echo":0.29290763051249086,"waveTo":7,"morph":{"start":0.8846746562048793,"end":0.1266201287508011,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.4423679542756264,"pitch":{"start":0.22577088101767004,"end":0,"curve":"Linear"},"tone":{"start":0.379898097156547,"end":0.11643098392058164,"curve":"Ease Out"},"vibrato":{"start":0.08002326404675841,"end":0.318109153280966,"curve":"Linear"},"level":{"start":1,"end":0.21108864131383598,"curve":"Linear"},"attack":0.003050813477762941,"release":0.3813516847203676,"resonance":0.8059129145811311,"echo":0.6191962610092014,"waveTo":7,"morph":{"start":0.21245999536477028,"end":0.5445417340612039,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":1.0314843715225979,"pitch":{"start":0.4125285191275179,"end":0.1825285191275179,"curve":"Ease Out"},"tone":{"start":0.727316748839803,"end":0.2842454736074433,"curve":"Ease Out"},"vibrato":{"start":0.013247315539047122,"end":0.30720369399059566,"curve":"Triangle"},"level":{"start":1,"end":0,"curve":"Steps"},"attack":0.007113685320845503,"release":0.8892106651056878,"resonance":0.4875037329387851,"echo":0.39657506674062465,"waveTo":7,"morph":{"start":0.41340553627815096,"end":0.3705517334397882,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.2129394718323399,"pitch":{"start":0.2054298087512143,"end":0.2550102163758129,"curve":"Bounce"},"tone":{"start":0.22415847649099307,"end":0.12872549208113923,"curve":"Steps"},"vibrato":{"start":0.9389264737255871,"end":0,"curve":"Bounce"},"level":{"start":0.5745716262143106,"end":0.5029359343927353,"curve":"Smooth"},"attack":0.014124168167822061,"release":0.10414270009318563,"resonance":0.42820823532529173,"echo":0.5351320885703899,"waveTo":7,"morph":{"start":0.9353192887268961,"end":0.9073241079924628,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":1,"duration":0.9298716458750832,"pitch":{"start":0.4082503354828805,"end":0.17825033548288047,"curve":"Linear"},"tone":{"start":0.5395693351980299,"end":0,"curve":"Linear"},"vibrato":{"start":0.1688344533322379,"end":0.150348775065504,"curve":"Ease In"},"level":{"start":0.8879578849300742,"end":0,"curve":"Linear"},"attack":0.006412907902586781,"release":0.8016134878233476,"resonance":0.2229054853436537,"echo":0,"waveTo":7,"morph":{"start":0.261685229325667,"end":0.5977564109722152,"curve":"Linear"}}]},{"id":"arcade_zaps","name":"Arcade Zaps","tip":"A sharp sawtooth zap with a quick diving pitch and a bright sting.","limits":{"waveType":2,"duration":[0.12,0.27],"attack":[0,0.003],"release":[0.075,0.18],"echo":0,"resonance":[0.2,0.45],"pitch.start":[0.67,0.84],"pitch.end":[0.18,0.3],"pitch.curve":"Ease Out","tone.start":[0.78,0.95],"tone.end":[0.25,0.45],"tone.curve":"Ease Out","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.75,0.95],"level.end":[0.08,0.25],"level.curve":"Ease Out"},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C157","C158","C159","C160","C161","C162","C163","C164","C165","C166","C167","C168"],"survey_source_ids":["T071","T091","T153","T505","T249","T384","T335","T220","T463","T281","T217","T382"],"exemplars":[{"masterVolume":0.5,"waveType":2,"duration":0.16021474966588972,"pitch":{"start":0.728150702180168,"end":0.18,"curve":"Ease Out"},"tone":{"start":0.8551105064970692,"end":0.42315531453750777,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9435676050538296,"end":0.10959008252610064,"curve":"Ease Out"},"attack":0.0009719776281211977,"release":0.1098505486876684,"resonance":0.28980893723818235,"echo":0,"waveTo":7,"morph":{"start":0.04854594892900157,"end":0.024040598316107047,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.27,"pitch":{"start":0.7961053126657219,"end":0.2602463995943709,"curve":"Ease Out"},"tone":{"start":0.8411946317743034,"end":0.45,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9412645254776131,"end":0.25,"curve":"Ease Out"},"attack":0.003,"release":0.17159196466508939,"resonance":0.4113334316417253,"echo":0,"waveTo":7,"morph":{"start":0.03788406125601635,"end":0.01828636421838669,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.1710864677698354,"pitch":{"start":0.7844444312292548,"end":0.2671849129131745,"curve":"Ease Out"},"tone":{"start":0.95,"end":0.45,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.95,"end":0.09787617359137925,"curve":"Ease Out"},"attack":0.0020328640408149674,"release":0.07862554710798134,"resonance":0.45,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.0014067152087156923,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.2192624457404556,"pitch":{"start":0.7663740708854425,"end":0.25462255687381746,"curve":"Ease Out"},"tone":{"start":0.825708997098941,"end":0.41210245880243357,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.95,"end":0.08,"curve":"Ease Out"},"attack":0.003,"release":0.1090855630326896,"resonance":0.37834291968488054,"echo":0,"waveTo":7,"morph":{"start":0.017402456806664336,"end":0.028682880699472727,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.17328291365163173,"pitch":{"start":0.7557708820027556,"end":0.24725131294937208,"curve":"Ease Out"},"tone":{"start":0.9013880504944004,"end":0.4398788826501894,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8369077910906692,"end":0.13224371080685524,"curve":"Ease Out"},"attack":0.002077879599369403,"release":0.08001428438650793,"resonance":0.2,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":2,"duration":0.12,"pitch":{"start":0.6799065443718143,"end":0.18405775667443638,"curve":"Ease Out"},"tone":{"start":0.8093413545943005,"end":0.25,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8649738300952271,"end":0.25,"curve":"Ease Out"},"attack":0.000005327428684538955,"release":0.075,"resonance":0.2,"echo":0,"waveTo":7,"morph":{"start":0.056599101004692,"end":0.05422643184523125,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.27,"pitch":{"start":0.84,"end":0.27894464395878255,"curve":"Ease Out"},"tone":{"start":0.7827054116933571,"end":0.25,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.75,"end":0.20250458816507405,"curve":"Ease Out"},"attack":0,"release":0.18,"resonance":0.28692010809321017,"echo":0,"waveTo":7,"morph":{"start":0.06,"end":0.05583092263391099,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.12,"pitch":{"start":0.8274424446513714,"end":0.3,"curve":"Ease Out"},"tone":{"start":0.7869675193789007,"end":0.4234089542375138,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.75,"end":0.23761364037411675,"curve":"Ease Out"},"attack":0.00003147850950884187,"release":0.075,"resonance":0.3863147338579578,"echo":0,"waveTo":7,"morph":{"start":0.010090812142217105,"end":0.06,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.12849688098268705,"pitch":{"start":0.84,"end":0.18,"curve":"Ease Out"},"tone":{"start":0.78,"end":0.25732221799017596,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9309009478505368,"end":0.16841724910891698,"curve":"Ease Out"},"attack":0.0016358199041532193,"release":0.08285395984903211,"resonance":0.3965099498435941,"echo":0,"waveTo":7,"morph":{"start":0.05534167366068376,"end":0,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.20315626713209667,"pitch":{"start":0.67,"end":0.18685893210274893,"curve":"Ease Out"},"tone":{"start":0.95,"end":0.43967497864353755,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8422200398504713,"end":0.08,"curve":"Ease Out"},"attack":0.0026901258213056405,"release":0.0989021795797165,"resonance":0.45,"echo":0,"waveTo":7,"morph":{"start":0,"end":0.006498084880854731,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.20939768697914166,"pitch":{"start":0.8375713988179339,"end":0.3,"curve":"Ease Out"},"tone":{"start":0.8238938406897095,"end":0.2625412061665029,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9300173167544116,"end":0.12852827983537773,"curve":"Ease Out"},"attack":0.002818042016699305,"release":0.10284841494311112,"resonance":0.37592933976924653,"echo":0,"waveTo":7,"morph":{"start":0.005985954568701868,"end":0.0051372335201246375,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.2670159900408481,"pitch":{"start":0.67,"end":0.21429222505884932,"curve":"Ease Out"},"tone":{"start":0.78,"end":0.3174209274525187,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9073123434554876,"end":0.22239237359640512,"curve":"Ease Out"},"attack":0,"release":0.18,"resonance":0.28999634787694917,"echo":0,"waveTo":7,"morph":{"start":0.06,"end":0.06,"curve":"Linear"}}]},{"id":"bubble_pops","name":"Bubble Pops","tip":"Round little water-note pops: a sine voice that curls up and back.","limits":{"waveTo":-1,"waveType":0,"duration":[0.12,0.28],"attack":[0.001,0.004],"release":[0.065,0.2],"echo":0,"resonance":[0.15,0.4],"pitch.start":[0.23,0.38],"pitch.end":[0.43,0.65],"pitch.curve":"Pulse","tone.start":[0.55,0.7],"tone.end":[0.5,0.65],"tone.curve":"Smooth","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.7,0.9],"level.end":[0.05,0.2],"level.curve":"Ease Out"},"intervals":{"pitch":[0.15,0.3]},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C169","C170","C171","C172","C173","C174","C175","C176","C177","C178","C179","C180"],"survey_source_ids":["T361","T333","T457","T201","T301","T073","T297","T365","T489","T233","T109","T163"],"exemplars":[{"masterVolume":0.5,"waveType":0,"duration":0.16837109610778897,"pitch":{"start":0.24443422740759352,"end":0.4409784405290115,"curve":"Pulse"},"tone":{"start":0.6163371914420737,"end":0.5,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7,"end":0.05219181947248462,"curve":"Ease Out"},"attack":0.0022166219302567763,"release":0.10799655526732305,"resonance":0.4,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.12589171819068018,"pitch":{"start":0.25886822182204844,"end":0.43,"curve":"Pulse"},"tone":{"start":0.6893663229640339,"end":0.65,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9,"end":0.2,"curve":"Ease Out"},"attack":0.0010009328976351268,"release":0.06559234031084171,"resonance":0.1737307152218501,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28,"pitch":{"start":0.31280478040218285,"end":0.5538617882125876,"curve":"Pulse"},"tone":{"start":0.5748427970840616,"end":0.5198065554953206,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7573284316218967,"end":0.05,"curve":"Ease Out"},"attack":0.003970199339993391,"release":0.19846260115988185,"resonance":0.15,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28,"pitch":{"start":0.3293635966236172,"end":0.5812012571342524,"curve":"Pulse"},"tone":{"start":0.55,"end":0.6004952472246199,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7932814294534413,"end":0.2,"curve":"Ease Out"},"attack":0.004,"release":0.2,"resonance":0.15,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.1891882400901545,"pitch":{"start":0.34482724370663265,"end":0.570703000119403,"curve":"Pulse"},"tone":{"start":0.7,"end":0.5612608303679929,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8867894848090639,"end":0.15654988726154537,"curve":"Ease Out"},"attack":0.0010473914412465783,"release":0.09509104105556275,"resonance":0.16488877081843537,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.2314273580348058,"pitch":{"start":0.23,"end":0.43,"curve":"Pulse"},"tone":{"start":0.5671252929160547,"end":0.5,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.8532326432589526,"end":0.2,"curve":"Ease Out"},"attack":0.003093547767775881,"release":0.1532366528078642,"resonance":0.3735224237431145,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.27389267857752775,"pitch":{"start":0.2830315955450598,"end":0.5047047077054286,"curve":"Pulse"},"tone":{"start":0.5560342240993045,"end":0.502946099692258,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7,"end":0.2,"curve":"Ease Out"},"attack":0.0036841145987996605,"release":0.1837036545731554,"resonance":0.4,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.12,"pitch":{"start":0.38,"end":0.65,"curve":"Pulse"},"tone":{"start":0.6671184716160707,"end":0.6445215141469391,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.785986047193515,"end":0.05435179183463364,"curve":"Ease Out"},"attack":0.001,"release":0.065,"resonance":0.34770705911191824,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.22605833795706604,"pitch":{"start":0.3486700753065526,"end":0.613077260036903,"curve":"Pulse"},"tone":{"start":0.55,"end":0.5625804093041081,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7349447678612928,"end":0.2,"curve":"Ease Out"},"attack":0.00301888060095622,"release":0.14938461679127946,"resonance":0.3403479782168061,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28,"pitch":{"start":0.37236738197333097,"end":0.65,"curve":"Pulse"},"tone":{"start":0.6214204597635237,"end":0.65,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.770343693320944,"end":0.19410460372140698,"curve":"Ease Out"},"attack":0.004,"release":0.2,"resonance":0.3747101748504439,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.12447948719931118,"pitch":{"start":0.38,"end":0.6301752601795058,"curve":"Pulse"},"tone":{"start":0.7,"end":0.5526740805130617,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.7333905727005446,"end":0.18467272842273852,"curve":"Ease Out"},"attack":0.001,"release":0.065,"resonance":0.32418261187126757,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.12,"pitch":{"start":0.23,"end":0.53,"curve":"Pulse"},"tone":{"start":0.6899707991967164,"end":0.5884937184800836,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.9,"end":0.05,"curve":"Ease Out"},"attack":0.0014927086457696592,"release":0.10988892791174472,"resonance":0.15875004394427045,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}}]},{"id":"rubber_clicks","name":"Rubber Clicks","tip":"Short rubbery ticks and cushioned clicks, kept close to the original voice.","limits":{"duration":[0.065,0.25],"echo":0},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C181","C182","C183","C184","C185","C186","C187","C188","C189","C190","C191","C192","C193","C194","C195","C196","C197","C198","C199","C200","C201","C202","C203","C204"],"survey_source_ids":["T362","T380","T075","T207","T430","T330","T239","T187","T456","T055","T251","T399","T082","T255","T092","T419","T475","T179","T363","T072","T076","T175","T028","T206"],"exemplars":[{"masterVolume":0.5,"waveType":2,"duration":0.1420333216212596,"pitch":{"start":0.20094144194154068,"end":0.5163404436036944,"curve":"Ease Out"},"tone":{"start":0.36000644899904727,"end":0.3887358807493001,"curve":"Linear"},"vibrato":{"start":0.633466474711895,"end":0.9799749786034226,"curve":"Pulse"},"level":{"start":0.8560695296619087,"end":0.7962220917176455,"curve":"Linear"},"attack":0.004881754777394234,"release":0.04617460398165738,"resonance":0.23397037187824024,"echo":0,"waveTo":7,"morph":{"start":0.7002082313410938,"end":0.7980924101313576,"curve":"Steps"}},{"masterVolume":0.5,"waveType":0,"duration":0.20671713905431421,"pitch":{"start":0.6514728453755378,"end":0.43637230434454977,"curve":"Bounce"},"tone":{"start":0.6815538225462661,"end":0.701281500456389,"curve":"Ease In"},"vibrato":{"start":0,"end":0.3228490736801177,"curve":"Triangle"},"level":{"start":0.6572617659810931,"end":0.6791826118342579,"curve":"Ease In"},"attack":0.05874805768158052,"release":0.05383852628746012,"resonance":0.17636308495420963,"echo":0,"waveTo":7,"morph":{"start":0.7390122496290132,"end":0.7393925611628219,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":2,"duration":0.13304893475888077,"pitch":{"start":0.5141186057240702,"end":0.27823968531563875,"curve":"Ease Out"},"tone":{"start":0.42705395139055324,"end":0.1586353457532823,"curve":"Triangle"},"vibrato":{"start":0,"end":0.9502532638143748,"curve":"Ease In"},"level":{"start":0.7565407301881351,"end":0.30624529032967984,"curve":"Linear"},"attack":0.05985318434000825,"release":0.08609327873764096,"resonance":0.00975981227820739,"echo":0,"waveTo":7,"morph":{"start":0.941250188741833,"end":0.5585417656693608,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":0,"duration":0.10779227988073196,"pitch":{"start":0.41748010994167994,"end":0.12140527221374213,"curve":"Smooth"},"tone":{"start":0.4533668368007056,"end":0.4304647151380777,"curve":"Bounce"},"vibrato":{"start":0.8688611453399062,"end":0,"curve":"Smooth"},"level":{"start":0.7455293631879613,"end":0.8345899651199579,"curve":"Ease Out"},"attack":0.00902235119557008,"release":0.021788628204781543,"resonance":0.013665240036789327,"echo":0,"waveTo":7,"morph":{"start":0.551503567956388,"end":0.42949041817337275,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.10527933088458612,"pitch":{"start":0.7400554683292285,"end":0.030062657510861752,"curve":"Smooth"},"tone":{"start":0.752686599351,"end":0.42315367490518835,"curve":"Linear"},"vibrato":{"start":0,"end":0.6307469469029456,"curve":"Triangle"},"level":{"start":0.41961408872157335,"end":0.8852501746453345,"curve":"Bounce"},"attack":0.010095242441631853,"release":0.06634725526861253,"resonance":0.2319900115719065,"echo":0,"waveTo":7,"morph":{"start":0.1145028049685061,"end":0.11967272744514049,"curve":"Steps"}},{"masterVolume":0.5,"waveType":3,"duration":0.18030988049370353,"pitch":{"start":0.5133893438894301,"end":0.7524363581836223,"curve":"Ease Out"},"tone":{"start":0.8559019419364631,"end":0.6090561673627235,"curve":"Linear"},"vibrato":{"start":0,"end":0,"curve":"Smooth"},"level":{"start":0.40969966462580487,"end":0.609641256192699,"curve":"Ease In"},"attack":0.006149917486589401,"release":0.09216890948839372,"resonance":0.2734802563441917,"echo":0,"waveTo":7,"morph":{"start":0.9055201816372573,"end":0.048773633781820536,"curve":"Linear"}},{"masterVolume":0.5,"waveType":3,"duration":0.0833022552600966,"pitch":{"start":0.6052014960511588,"end":0.07538226921111345,"curve":"Smooth"},"tone":{"start":0.3249092191806994,"end":0.3475195087958127,"curve":"Ease Out"},"vibrato":{"start":0.5257269074209034,"end":0,"curve":"Ease Out"},"level":{"start":0.566497631277889,"end":0.4144198641739786,"curve":"Smooth"},"attack":0.014632353921420871,"release":0.026419017038753996,"resonance":0.08575211983406916,"echo":0,"waveTo":7,"morph":{"start":0.722507508425042,"end":0.936716315546073,"curve":"Steps"}},{"masterVolume":0.5,"waveType":1,"duration":0.25,"pitch":{"start":0.4619001218327321,"end":0.3482724138069898,"curve":"Bounce"},"tone":{"start":0.31038997108116745,"end":0.7895576070295647,"curve":"Smooth"},"vibrato":{"start":0.9325111645739526,"end":0.19249493605457246,"curve":"Ease In"},"level":{"start":0.8105167681351304,"end":0.5271928941458464,"curve":"Triangle"},"attack":0.027155742729082704,"release":0.04316254162695259,"resonance":0.4814315609168261,"echo":0,"waveTo":7,"morph":{"start":0.004805619576945901,"end":0.1329367236653343,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":0,"duration":0.11851355132103536,"pitch":{"start":0.5140191318606958,"end":0.282592387329787,"curve":"Ease In"},"tone":{"start":0.3924962060176767,"end":0.05322111310670152,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Pulse"},"level":{"start":0.6393470690120011,"end":0.26423187578096985,"curve":"Triangle"},"attack":0.00195238015986979,"release":0.02481511895545419,"resonance":0.21963753156596794,"echo":0,"waveTo":7,"morph":{"start":0.6649408733937889,"end":0.7868261765688658,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":0,"duration":0.25,"pitch":{"start":0.20206651587272062,"end":0.5656295605842024,"curve":"Pulse"},"tone":{"start":0.7897592675755731,"end":0.30758177071111276,"curve":"Ease In"},"vibrato":{"start":0.453798747388646,"end":0.3079364122822881,"curve":"Pulse"},"level":{"start":0.3960902832332067,"end":0.18354562317952516,"curve":"Pulse"},"attack":0.0024150460993318267,"release":0.025027878917753696,"resonance":0.14057438037125394,"echo":0,"waveTo":7,"morph":{"start":0.10963310717605054,"end":0.1935542155522853,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":1,"duration":0.10620017364714342,"pitch":{"start":0.11755241600330919,"end":0.21547999948263166,"curve":"Bounce"},"tone":{"start":0.36732453565346074,"end":0.5961264932644553,"curve":"Ease Out"},"vibrato":{"start":0.2544450021814555,"end":0.4579049274325371,"curve":"Smooth"},"level":{"start":0.8854524818831123,"end":0.984549922440201,"curve":"Smooth"},"attack":0.010954777748789637,"release":0.016712546938371497,"resonance":0.04062496181577444,"echo":0,"waveTo":7,"morph":{"start":0.8488382233073934,"end":0.8259326143655925,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.1596246969541044,"pitch":{"start":0.41686121416976674,"end":0.3837273567449301,"curve":"Smooth"},"tone":{"start":0.8288334650103935,"end":0.3557131754234433,"curve":"Triangle"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.48526954469271,"end":0.2699597168713808,"curve":"Ease Out"},"attack":0.06562555646801926,"release":0.08593584546746232,"resonance":0.8572064334060996,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.16937548249094792,"pitch":{"start":0.6392406934197061,"end":0.43862208412028847,"curve":"Triangle"},"tone":{"start":0.7956146385986358,"end":0.4235303059918806,"curve":"Bounce"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.6115708504803479,"end":0.7134663586504757,"curve":"Ease Out"},"attack":0.017119431857485323,"release":0.04452246377091176,"resonance":0.8282763205352239,"echo":0,"waveTo":7,"morph":{"start":0.281831517117098,"end":0.0477569738868624,"curve":"Steps"}},{"masterVolume":0.5,"waveType":1,"duration":0.13620229052748564,"pitch":{"start":0.24089209570549427,"end":0.6740630068350583,"curve":"Steps"},"tone":{"start":0.8046714015072212,"end":0.2892943404847756,"curve":"Pulse"},"vibrato":{"start":0,"end":0,"curve":"Ease In"},"level":{"start":0.40265412885928525,"end":0.10115455561317505,"curve":"Triangle"},"attack":0.002767405344173312,"release":0.05509240896512689,"resonance":0.23006403414765372,"echo":0,"waveTo":7,"morph":{"start":0.7974923822330311,"end":0.9180549492128194,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":1,"duration":0.08815439427761801,"pitch":{"start":0.70681925162673,"end":0.49436723405495286,"curve":"Bounce"},"tone":{"start":0.786211387149524,"end":0.2847856806940399,"curve":"Pulse"},"vibrato":{"start":0,"end":0.7664118178654462,"curve":"Bounce"},"level":{"start":0.7117946098209358,"end":0.9362469850666821,"curve":"Ease In"},"attack":0.002266687040682882,"release":0.049079766862539335,"resonance":0.018646800820715726,"echo":0,"waveTo":7,"morph":{"start":0.20850667729973793,"end":0.26657537720166147,"curve":"Bounce"}},{"masterVolume":0.5,"waveType":2,"duration":0.10524172644534495,"pitch":{"start":0.5863758140522987,"end":0.11561108523048459,"curve":"Linear"},"tone":{"start":0.19386255403514951,"end":0.6832880237023347,"curve":"Smooth"},"vibrato":{"start":0.7862237028311938,"end":0,"curve":"Smooth"},"level":{"start":0.5464945257641375,"end":0.8452863472048193,"curve":"Linear"},"attack":0.012032329324632883,"release":0.019291151633913043,"resonance":0.539213168527931,"echo":0,"waveTo":7,"morph":{"start":0.1526516949571669,"end":0.028737932317890225,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":1,"duration":0.1570298180811344,"pitch":{"start":0.6528817008831539,"end":0.8035329618398099,"curve":"Bounce"},"tone":{"start":0.40188990806927904,"end":0.18227119173388928,"curve":"Ease In"},"vibrato":{"start":0.6688656667247415,"end":0,"curve":"Triangle"},"level":{"start":0.5031830221647396,"end":0.1914413824863732,"curve":"Smooth"},"attack":0.046929770912667305,"release":0.03370906729320527,"resonance":0.5833791793440468,"echo":0,"waveTo":7,"morph":{"start":0.5459343756083399,"end":0.840397167019546,"curve":"Ease Out"}},{"masterVolume":0.5,"waveType":3,"duration":0.196853868646739,"pitch":{"start":0.5352169018099084,"end":0.15401895355433226,"curve":"Triangle"},"tone":{"start":0.5578506942954846,"end":0.7985769069171511,"curve":"Triangle"},"vibrato":{"start":0,"end":0,"curve":"Pulse"},"level":{"start":0.7805816864245572,"end":0.521690215934068,"curve":"Triangle"},"attack":0.008584206552710383,"release":0.13212321963565016,"resonance":0.010844697756692766,"echo":0,"waveTo":7,"morph":{"start":0.1124784308951348,"end":0.20927321917377412,"curve":"Ease Out"}},{"masterVolume":0.5,"waveType":0,"duration":0.10941656791917712,"pitch":{"start":0.24354268037248403,"end":0.6889499582815916,"curve":"Ease Out"},"tone":{"start":0.8646531982230954,"end":0.061998971586581325,"curve":"Triangle"},"vibrato":{"start":0,"end":0.3278184710070491,"curve":"Linear"},"level":{"start":0.6775244043208659,"end":0.2910371345560998,"curve":"Triangle"},"attack":0.015277449719142168,"release":0.025243446616143504,"resonance":0.6123375896015204,"echo":0,"waveTo":7,"morph":{"start":0.7743371824966743,"end":0.8023435984039679,"curve":"Ease In"}},{"masterVolume":0.5,"waveType":3,"duration":0.11766215768223477,"pitch":{"start":0.7103986685327255,"end":0.43365778179839254,"curve":"Ease In"},"tone":{"start":0.6708668337319977,"end":0.5748289911076426,"curve":"Linear"},"vibrato":{"start":0.09077644068747759,"end":0.4563755465205759,"curve":"Bounce"},"level":{"start":0.7482656282605603,"end":0.3847853032499552,"curve":"Ease In"},"attack":0.013841457528993486,"release":0.02002108985589858,"resonance":0.5394325149129144,"echo":0,"waveTo":7,"morph":{"start":0.5371237676590681,"end":0.12400691071525216,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":2,"duration":0.07811376780105872,"pitch":{"start":0.6596356546785682,"end":0.6571510599926114,"curve":"Ease Out"},"tone":{"start":0.766846251685638,"end":0.15816896453034132,"curve":"Bounce"},"vibrato":{"start":0.3092624528799206,"end":0.14857748243957758,"curve":"Steps"},"level":{"start":0.5074717861483805,"end":0.9623866765014827,"curve":"Ease In"},"attack":0.03126414904631015,"release":0.020908383060108875,"resonance":0.4192904700874351,"echo":0,"waveTo":7,"morph":{"start":0.8696790884714574,"end":0.8412782209925354,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":3,"duration":0.12442590287118573,"pitch":{"start":0.4801519318646751,"end":0.7322018309962004,"curve":"Smooth"},"tone":{"start":0.5571643601870164,"end":0.19904875898500907,"curve":"Steps"},"vibrato":{"start":0,"end":0,"curve":"Steps"},"level":{"start":0.8644198861205951,"end":0.7187478881701826,"curve":"Bounce"},"attack":0.007668204626999795,"release":0.02124449947421323,"resonance":0.9084655384183861,"echo":0,"waveTo":7,"morph":{"start":0.1476644038874656,"end":0.10575845252722502,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":0,"duration":0.13987807896585586,"pitch":{"start":0.8134248842136004,"end":0.21409397369250655,"curve":"Bounce"},"tone":{"start":0.8330414347932674,"end":0.9623574990779161,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Ease Out"},"level":{"start":0.9945459286333062,"end":0.8381930396426469,"curve":"Pulse"},"attack":0.01336446389229968,"release":0.0370599003891024,"resonance":0.27127344594337044,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.11164540828326112,"pitch":{"start":0.19747088808333502,"end":0.23166122428141533,"curve":"Smooth"},"tone":{"start":0.43733639792772006,"end":0.19444215754047034,"curve":"Bounce"},"vibrato":{"start":0.9604660393670201,"end":0,"curve":"Smooth"},"level":{"start":0.6892697806702927,"end":0.8276342302002012,"curve":"Ease In"},"attack":0.02878359595570294,"release":0.06763542175266707,"resonance":0.43328724274178965,"echo":0,"waveTo":7,"morph":{"start":0.7845137596596032,"end":0.8941242636647075,"curve":"Triangle"}}]},{"id":"bubble_swells","name":"Bubble Swells","tip":"A rounded sine bloop that swells to a small peak, then stops.","limits":{"waveTo":-1,"waveType":0,"duration":[0.28,0.5],"attack":[0.19,0.36],"release":[0.035,0.065],"echo":0,"resonance":[0.08,0.25],"pitch.start":[0.37,0.5],"pitch.end":[0.4,0.55],"pitch.curve":"Smooth","tone.start":[0.47,0.62],"tone.end":[0.55,0.7],"tone.curve":"Smooth","vibrato.start":0,"vibrato.end":0,"vibrato.curve":"Linear","level.start":[0.35,0.55],"level.end":[0.65,0.85],"level.curve":"Ease In"},"intervals":{"pitch":[0,0.055]},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C205","C206","C207","C208","C209","C210","C211","C212","C213","C214","C215","C216"],"survey_source_ids":["T502","T269","T141","T237","T063","T340","T173","T170","T040","T397","T045","T487"],"exemplars":[{"masterVolume":0.5,"waveType":0,"duration":0.4778668048002124,"pitch":{"start":0.5,"end":0.5,"curve":"Smooth"},"tone":{"start":0.5296546375105197,"end":0.55,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5437820230298945,"end":0.7533740291929077,"curve":"Ease In"},"attack":0.36,"release":0.038521033910789884,"resonance":0.19915692089261727,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.2978535004889773,"pitch":{"start":0.37,"end":0.425,"curve":"Smooth"},"tone":{"start":0.5409887372451387,"end":0.7,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.4612944826660742,"end":0.7684397668527564,"curve":"Ease In"},"attack":0.1903866679260373,"release":0.03757600421008722,"resonance":0.11287283506232905,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28540477737775666,"pitch":{"start":0.4516079849715563,"end":0.5066079849715563,"curve":"Smooth"},"tone":{"start":0.62,"end":0.6432612473409327,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.42680886184765515,"end":0.7511888707723912,"curve":"Ease In"},"attack":0.19010636548202045,"release":0.03577983190401687,"resonance":0.08,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.5,"pitch":{"start":0.4324483227724081,"end":0.48744832277240807,"curve":"Smooth"},"tone":{"start":0.6035336147645294,"end":0.6960558792544004,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.4177429303041058,"end":0.8437094651630278,"curve":"Ease In"},"attack":0.19498699216137402,"release":0.065,"resonance":0.11717276789285352,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.38964936903359837,"pitch":{"start":0.5,"end":0.5,"curve":"Smooth"},"tone":{"start":0.47,"end":0.6498175344802796,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.65,"curve":"Ease In"},"attack":0.32322672260148044,"release":0.042859744278247014,"resonance":0.25,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.48054229278855076,"pitch":{"start":0.38703609805859895,"end":0.44203609805859895,"curve":"Smooth"},"tone":{"start":0.5192629921209699,"end":0.55,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.4367084703754784,"end":0.65,"curve":"Ease In"},"attack":0.3533534337566279,"release":0.038308549420478205,"resonance":0.1685234840410363,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28,"pitch":{"start":0.3869048262148417,"end":0.4419048262148417,"curve":"Smooth"},"tone":{"start":0.6059657390234325,"end":0.6809438978250085,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5331368486275107,"end":0.85,"curve":"Ease In"},"attack":0.19,"release":0.035,"resonance":0.25,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.28,"pitch":{"start":0.37,"end":0.4,"curve":"Smooth"},"tone":{"start":0.62,"end":0.6629407497577687,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.35,"end":0.738702961030794,"curve":"Ease In"},"attack":0.223660001083421,"release":0.035,"resonance":0.24958474519910429,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.5,"pitch":{"start":0.48889207158970505,"end":0.5195567947809578,"curve":"Smooth"},"tone":{"start":0.4746696823722945,"end":0.6882264600557613,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.35,"end":0.782198567057635,"curve":"Ease In"},"attack":0.36,"release":0.065,"resonance":0.22322196764379293,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.3597509081004905,"pitch":{"start":0.43569999401823906,"end":0.49069999401823905,"curve":"Smooth"},"tone":{"start":0.5505816857700658,"end":0.7,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5219980777640842,"end":0.85,"curve":"Ease In"},"attack":0.19178038473352077,"release":0.04650691289654823,"resonance":0.08,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.2801560244977973,"pitch":{"start":0.4819318914954517,"end":0.5369318914954517,"curve":"Smooth"},"tone":{"start":0.5710717552564446,"end":0.7,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.5433501517644999,"end":0.834476234389905,"curve":"Ease In"},"attack":0.19,"release":0.035022512098591016,"resonance":0.165220047747412,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":0,"duration":0.29158965007925114,"pitch":{"start":0.3985557313720139,"end":0.4535557313720139,"curve":"Smooth"},"tone":{"start":0.47,"end":0.5502997730836303,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Linear"},"level":{"start":0.55,"end":0.8454747626138985,"curve":"Ease In"},"attack":0.21201043010580112,"release":0.037132266726003796,"resonance":0.17806648721247637,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}}]},{"id":"static_flecks","name":"Radio Spits","tip":"Brief fragments of filtered radio grit, dry and rough around the edges.","limits":{"duration":[0.065,0.32],"echo":0},"intervals":{},"variation":{"pitch":0.035,"tone":0.06,"vibrato":0.05,"level":0.06,"morph":0.025},"source_ids":["C217","C218","C219","C220","C221","C222","C223","C224","C225","C226","C227","C228"],"survey_source_ids":["T228","T142","T079","T373","T122","T507","T368","T189","T100","T124","T127","T482"],"exemplars":[{"masterVolume":0.5,"waveType":2,"duration":0.2887377278661118,"pitch":{"start":0.583982234406285,"end":0.43687783951871095,"curve":"Linear"},"tone":{"start":0.32238762128399684,"end":0.8595635533798486,"curve":"Linear"},"vibrato":{"start":0,"end":0.2630241254810244,"curve":"Bounce"},"level":{"start":0.6482595054083504,"end":0.8918333322182298,"curve":"Bounce"},"attack":0.12329430493571086,"release":0.19800040923477405,"resonance":0.39551904071122407,"echo":0,"waveTo":7,"morph":{"start":0.9729269415605813,"end":0.7429677043110132,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":3,"duration":0.0856110717485482,"pitch":{"start":0.43813916814280673,"end":0.9430671793594956,"curve":"Smooth"},"tone":{"start":0.25100738208275286,"end":0.6509813783108257,"curve":"Triangle"},"vibrato":{"start":0,"end":0.664141257526353,"curve":"Bounce"},"level":{"start":0.4882844342733733,"end":0.8839368013478816,"curve":"Smooth"},"attack":0.0098142941147089,"release":0.04043416352106621,"resonance":0.3610868851887062,"echo":0,"waveTo":-1,"morph":{"start":0,"end":1,"curve":"Smooth"}},{"masterVolume":0.5,"waveType":1,"duration":0.13492025695136922,"pitch":{"start":0.2519951627869159,"end":0.9489862996526062,"curve":"Smooth"},"tone":{"start":0.9605587352532894,"end":0.4744555362151004,"curve":"Pulse"},"vibrato":{"start":0,"end":0,"curve":"Ease Out"},"level":{"start":0.8433726495830343,"end":0.9462453911453486,"curve":"Bounce"},"attack":0.011868494323454796,"release":0.0706854870379585,"resonance":0.6334500038065016,"echo":0,"waveTo":7,"morph":{"start":0.10792408976703882,"end":0.13695984706282616,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":2,"duration":0.28482411027922655,"pitch":{"start":0.5225489816907793,"end":0.7525489816907793,"curve":"Triangle"},"tone":{"start":0.5652477274881675,"end":0.7961880306247622,"curve":"Linear"},"vibrato":{"start":0,"end":0.7660948911914602,"curve":"Steps"},"level":{"start":0.6977482959162444,"end":0.6117502267705277,"curve":"Smooth"},"attack":0.007767930280342542,"release":0.07767930280342542,"resonance":0.5397573336143978,"echo":0,"waveTo":7,"morph":{"start":0.20136982947587967,"end":0.23633194284047931,"curve":"Linear"}},{"masterVolume":0.5,"waveType":0,"duration":0.32,"pitch":{"start":0.802913196994923,"end":0.44315274440683416,"curve":"Bounce"},"tone":{"start":0.47244302784092723,"end":0.9774011564790271,"curve":"Ease Out"},"vibrato":{"start":0.038961051031947136,"end":0,"curve":"Bounce"},"level":{"start":0.5644842738634906,"end":0.4906991615518928,"curve":"Pulse"},"attack":0.002900172774666619,"release":0.19895848762989046,"resonance":0.9423457934870384,"echo":0,"waveTo":7,"morph":{"start":0.8486716058803723,"end":0.8940062249079347,"curve":"Linear"}},{"masterVolume":0.5,"waveType":1,"duration":0.16214419659357784,"pitch":{"start":0.37926974693778903,"end":0.7118098172452301,"curve":"Bounce"},"tone":{"start":0.3586813791305758,"end":0.9752027669688687,"curve":"Steps"},"vibrato":{"start":0,"end":0.4958445120137185,"curve":"Smooth"},"level":{"start":0.5540144366561435,"end":0.9989442552253603,"curve":"Ease Out"},"attack":0.0023476520301774144,"release":0.05873882726069844,"resonance":0.15672193710925056,"echo":0,"waveTo":7,"morph":{"start":0.8207641430897638,"end":0.8849524765042588,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.32,"pitch":{"start":0.38509061224758623,"end":0.4211178614012897,"curve":"Smooth"},"tone":{"start":0.47757378112291915,"end":0.7353914228151552,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Pulse"},"level":{"start":0.8979807821568102,"end":0.18170958179980518,"curve":"Linear"},"attack":0.003201882828292698,"release":0.05162626972198488,"resonance":0.34544677276862784,"echo":0,"waveTo":7,"morph":{"start":0.8270683194277808,"end":0.7719108653720468,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":2,"duration":0.32,"pitch":{"start":0.10998916151933372,"end":0.04998916151933371,"curve":"Linear"},"tone":{"start":0.3682255243230611,"end":1,"curve":"Linear"},"vibrato":{"start":0,"end":0.059389802021905774,"curve":"Ease In"},"level":{"start":0.8717430339194834,"end":0.7212077794130891,"curve":"Pulse"},"attack":0.03339130434782609,"release":0.13913043478260873,"resonance":0.7948596247588284,"echo":0,"waveTo":7,"morph":{"start":1,"end":0.8582461592741311,"curve":"Linear"}},{"masterVolume":0.5,"waveType":2,"duration":0.14031430060637293,"pitch":{"start":0.31937992241000757,"end":0.6206015685480087,"curve":"Linear"},"tone":{"start":0.19660655315965414,"end":0.8699836116167716,"curve":"Bounce"},"vibrato":{"start":0.3931834704708308,"end":0.9797578111756593,"curve":"Linear"},"level":{"start":0.932238993968349,"end":0.5761677767895163,"curve":"Steps"},"attack":0.015652741705533116,"release":0.07779057087298089,"resonance":0.37973660172428936,"echo":0,"waveTo":7,"morph":{"start":0.7632776892278343,"end":0.9133065393893048,"curve":"Triangle"}},{"masterVolume":0.5,"waveType":0,"duration":0.1680264479624581,"pitch":{"start":0.8676242127595469,"end":0.8225412659905851,"curve":"Bounce"},"tone":{"start":0.21674886023392903,"end":0.7859426465816796,"curve":"Ease Out"},"vibrato":{"start":0,"end":0,"curve":"Bounce"},"level":{"start":0.7905298234545626,"end":0.7451236844621598,"curve":"Bounce"},"attack":0.01280828048614785,"release":0.08927789215277449,"resonance":0.4965215620817616,"echo":0,"waveTo":7,"morph":{"start":0.8242679443676024,"end":0.9187677669338882,"curve":"Steps"}},{"masterVolume":0.5,"waveType":2,"duration":0.13330741153118247,"pitch":{"start":0.4758688971516676,"end":0.4052496506180614,"curve":"Steps"},"tone":{"start":0.1503565368009731,"end":0.8964988313149661,"curve":"Bounce"},"vibrato":{"start":0.5950054114218801,"end":0,"curve":"Steps"},"level":{"start":0.3642114775720984,"end":0.9920195976924151,"curve":"Smooth"},"attack":0.00269232688145712,"release":0.04247805107804092,"resonance":0.10042165708728135,"echo":0,"waveTo":7,"morph":{"start":0.8086341974558309,"end":0.9142858313629404,"curve":"Pulse"}},{"masterVolume":0.5,"waveType":3,"duration":0.20867308580763375,"pitch":{"start":0.8319777548220009,"end":0.5877241367287933,"curve":"Linear"},"tone":{"start":0.44497428621398283,"end":0.8018899344955571,"curve":"Smooth"},"vibrato":{"start":0,"end":0,"curve":"Triangle"},"level":{"start":0.8572588854120113,"end":0.3266404113266617,"curve":"Bounce"},"attack":0.051661145606734155,"release":0.06140141295153025,"resonance":0.9344400093541481,"echo":0,"waveTo":7,"morph":{"start":0.8833653597859665,"end":0.8707963404478505,"curve":"Pulse"}}]}];

// js/synths/Bfxr.js
class Bfxr extends SynthBase {
    /*********************/
    /*      METADATA     */
    /*********************/

    name = "Bfxr";
    version = Bfxr_DSP.version;
    tooltip = "Bfxr is a simple sound effect generator, based on DrPetter's Sfxr.";

    canvas_bg_logo = "img/logo_bfxr.png";

    header_properties = ["waveType"];

    permalocked = ["masterVolume"];
    hide_params = ["masterVolume"];

    param_info = [
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume", 0.5, 0, 1
        ],
        {
            type: "BUTTONSELECT",

            name: "waveType",
            display_name: "",
            tooltip: "",

            default_value: 0,
            columns: 4,
            header: true,

            values: [
                [
                    "Triangle",
                    "Triangle waves are robust at all frequencies, stand out quite well in most situations, and have a clear, resonant quality.",
                    4
                ],
                [
                    "Sin",
                    "Sin waves are the most elementary of all wave-types.  However, they can be sensitive to context (background noise or accoustics can drown them out sometimes), so be careful.",
                    2
                ],
                [
                    "Square",
                    "quare waves can be quite powerful.  They have two extra properties, Square Duty and Duty Sweep, that can further control the timbre of the wave.",
                    0
                ],
                [
                    "Saw",
                    "Saw waves are pretty raspy",
                    1
                ],
                [
                    "Breaker",
                    "These are defined by a quadratic equation (a=t*t%1, giving a toothed-shaped), making them a little more hi-fi than other wave-types on this list.  For the most part, like a smoother, slicker triangle wave.",
                    8
                ],
                [
                    "Tan",
                    "A potentially crazy wave.  Does strange things.  Tends to produce plenty of distortion	 (because the basic shape goes outside of the standard waveform range).",
                    6
                ],
                [
                    "Whistle",
                    "A sin wave with an additional sine wave overlayed at a lower amplitude and 20x the frequency.  It can end up sounding buzzy, hollow, resonant, or breathy.",
                    7
                ],
                [
                    "White",
                    "White noise is your bog standard random number stream.  Quite hard-sounding, compared to pink noise.",
                    3
                ],
                [
                    "Voice",
                    "A digital voice sample.",
                    11
                ],
                [
                    "Bitnoise",
                    "Periodic 1-bit \"white\" noise. Useful for glitchy and punky sound effects.",
                    9
                ],
                [
                    "Rasp",
                    "Periodic 1-bit noise with a shortened period. It makes a nice digital buzz or clang sound.",
                    5
                ],
                [
                    "FMSyn",
                    "A pretty dense mix of lots of waveforms.  Breathier/distorteder than the classic ones.",
                    10
                ],
            ]
        },
        [
            "Attack Time",
            "Length of the volume envelope attack.",
            "attackTime", 0, 0, 1
        ],
        [
            "Sustain Time",
            "Length of the volume envelope sustain.",
            "sustainTime", 0.3, 0, 1
        ],
        [
            "Punch",
            "Tilts the sustain envelope for more 'pop'.",
            "sustainPunch", 0, 0, 1
        ],
        [
            "Decay Time",
            "Length of the volume envelope decay (yes, I know it's called release).",
            "decayTime", 0.4, 0.03, 1
        ],
        [
            "Compression",
            "Pushes amplitudes together into a narrower range to make them stand out more.  Very good for sound effects, where you want them to stick out against background music. If unlocked, this is set to zero during randomization.",
            "compressionAmount", 0, 0, 1
        ],
        [
            "Frequency",
            "Base note of the sound.",
            "frequency_start", 0.3, 0, 1
        ],
        [
            "Frequency Slide",
            "Slides the frequency up or down.",
            "frequency_slide", 0.0, -0.5, 0.5
        ],
        [
            "Delta Slide",
            "Accelerates the frequency.  Can be used to get the frequency to change direction.",
            "frequency_acceleration", 0.0, -1, 1
        ],
        [
            "Frequency Cutoff",
            "If sliding, the sound will stop at this frequency, to prevent really low notes.  0 means no cuttoff, 1 refers to the starting frequency of the sound. Ignores vibrato.  If the sound trajectory only goes up, this is disabled.",
            "min_frequency_relative_to_starting_frequency", 0.0, 0, 0.99
        ],
        [
            "Vibrato Depth",
            "Strength of the vibrato effect.",
            "vibratoDepth", 0, 0, 1
        ],
        [
            "Vibrato Speed",
            "Speed of the vibrato effect (i.e. frequency).",
            "vibratoSpeed", 0, 0, 1
        ],
        [
            "Pitch Jump Repeat Speed",
            "Larger Values means more pitch jumps, which can be useful for arpeggiation. 0 means a single jump in the whole sound, 1 means 50 jumps a second.",
            "pitch_jump_repeat_speed", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 1",
            "Jump in pitch, either up or down.",
            "pitch_jump_amount", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 1",
            "When the first pitch-jump happens.",
            "pitch_jump_onset_percent", 0, 0, 1
        ],
        [
            "Pitch Jump Amount 2",
            "Second jump in pitch, either up or down.",
            "pitch_jump_2_amount", 0, -1, 1
        ],
        [
            "Pitch Jump Onset 2",
            "When the second pitch-jump happens.",
            "pitch_jump_onset2_percent", 0, 0, 1
        ],
        [
            "Harmonics",
            "Overlays copies of the waveform with copies and multiples of its frequency.  Good for bulking out or otherwise enriching the texture of the sounds (warning: this is the number 1 cause of bfxr slowdown!).",
            "overtones", 0, 0, 1
        ],
        [
            "Harmonics Falloff",
            "The rate at which higher overtones should decay.",
            "overtoneFalloff", 0, 0, 1
        ],
        [
            "Square Duty",
            "Square waveform only : Controls the ratio between the up and down states of the square wave, changing the timbre.",
            "squareDuty", 0, 0, 0.99
        ],
        [
            "Duty Sweep",
            "Square waveform only : Sweeps the duty up or down.",
            "dutySweep", 0, -1, 1
        ],
        [
            "Repeat Speed",
            "Speed of the note repeating - certain variables are reset each time (sweeps, pitch slide, delta slide, etc. - doesn't apply to pitch jumps which have their own repeat parameter). 0 means no repeat, 1 means 10 repeats a second.",
            "repeatSpeed", 0, 0, 1
        ],
        [
            "Flanger Offset",
            "Offsets a second copy of the wave by a small phase, changing the timbre.",
            "flangerOffset", 0, -1, 1
        ],
        [
            "Flanger Sweep",
            "Sweeps the phase up or down.",
            "flangerSweep", 0, -1, 1
        ],
        [
            "Low-pass Filter Cutoff",
            "Frequency at which the low-pass filter starts attenuating higher frequencies.  Named most likely to result in 'Huh why can't I hear anything?' at her high-school grad. ",
            "lpFilterCutoff", 1, 0.01, 1
        ],
        [
            "Low-pass Filter Cutoff Sweep",
            "Sweeps the low-pass cutoff up or down.",
            "lpFilterCutoffSweep", 0, -1, 1
        ],
        [
            "Low-pass Filter Resonance",
            "Changes the attenuation rate for the low-pass filter, changing the timbre.",
            "lpFilterResonance", 0, 0, 1
        ],
        [
            "High-pass Filter Cutoff",
            "Frequency at which the high-pass filter starts attenuating lower frequencies.",
            "hpFilterCutoff", 0, 0, 1
        ],
        [
            "High-pass Filter Cutoff Sweep",
            "Sweeps the high-pass cutoff up or down.",
            "hpFilterCutoffSweep", 0, -1, 1
        ],
        [
            "Bit Crush",
            "Resamples the audio at a lower frequency.",
            "bitCrush", 0, 0, 1
        ],
        [
            "Bit Crush Sweep",
            "Sweeps the Bit Crush filter up or down.",
            "bitCrushSweep", 0, -1, 1
        ]
    ];

    templates = [
        [
            "Pickup/Coin",
            "Blips and baleeps.  Try messing with the wave-forms to get your own sound.",
            "generate_pickup_coin",
            "Pickup",
        ],
        [
            "Laser/Shoot",
            "Pew pew.  Try playing about with the Frequency properties (slide + delta slide especially).  If you want to add some texture, try adding some light, high-frequency vibrato.",
            "generate_laser_shoot",
            "Shoot"
        ],
        [
            "Explosion",
            "Boom.  To make this louder, try increasing compression, or fiddling with the frequency parameters.  To make this softer, try switching to pink noise or decreasing the frequency.  If you're hearing nothing after messing with parameters, try fiddling with 'frequency cutoff'.",
            "generate_explosion",
            "Boom"

        ],
        [
            "Powerup",
            "Whoo.  Try messing with the slide + delta slide parameters to make these less unreservedly exhuberant.  Or how about increasing the decay and playing with the Pitch Jump/Onset parameters?",
            "generate_powerup",
            "PowerUp"
        ],
        [
            "Hit/Hurt",
            "If you want something more crackly, try out a tan wave here.",
            "generate_hit_hurt",
            "Hit"
        ],
        [
            "Jump",
            "Try turn your jump into a soggy kiss with some bitcrush.",
            "generate_jump",
            "Jump"
        ],
        [
            "Blip/Select",
            "You might want to make a variation of this with longer decay for blips that accompany fadeouts or animations.",
            "generate_blip_select",
            "Blip"
        ],
        [
            "Randomize",
            "Talking your life into your hands... (only modifies unlocked parameters)",
            "randomize_params",
            "Random"
        ],
        [
            "Mutate",
            "Modify each unlocked parameter by a small wee amount... (only modifies unlocked parameters)",
            "mutate_params",
            "Mutant"
        ],
    ];

    /*********************/
    /* CONSTRUCTOR       */
    /*********************/

    constructor() {
        super();
        this.post_initialize();
    }

    /*********************/
    /*TEMPLATE FUNCTIONS */
    /*********************/

    generate_sin() {
        this.reset_params(true);
        this.set_param("waveType", 1, true);
    }

    generate_pickup_coin() {
        this.reset_params(true);

        this.set_param("frequency_start", 0.4 + Math.random() * 0.5, true);

        this.set_param("sustainTime", Math.random() * 0.1, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.4, true);
        this.set_param("sustainPunch", 0.3 + Math.random() * 0.3, true);

        if (Math.random() < 0.5) {
            this.set_param("pitch_jump_onset_percent", 0.5 + Math.random() * 0.2, true);
            var cnum = Math.floor(Math.random() * 7) + 1;
            var cden = Math.floor(Math.random() * 7) + cnum + 2;

            this.set_param("pitch_jump_amount", cnum / cden, true);
        }
    }

    generate_laser_shoot() {
        this.reset_params(true);
        this.set_param("waveType", (Math.random() * 3)|0, true);
        if (this.get_param("waveType") == 2 && Math.random() < 0.5) {
            this.set_param("waveType",
                (Math.random() * 2)|0, true);
        }

        if (Math.random() < 0.33) {
            this.set_param("frequency_start", 0.1+Math.random() * 0.5, true);
            this.set_param("min_frequency_relative_to_starting_frequency", Math.random() * 0.1, true);
            this.set_param("frequency_slide", -0.35 - Math.random() * 0.3, true);
        } else {
            this.set_param("frequency_start",
                0.5 + Math.random() * 0.5, true);
            this.set_param("min_frequency_relative_to_starting_frequency",
                this.get_param("frequency_start") - 0.2 - Math.random() * 0.6, true);

            if (this.get_param("min_frequency_relative_to_starting_frequency") < 0.2)
                this.set_param("min_frequency_relative_to_starting_frequency", 0.2, true);

            this.set_param("frequency_slide", -0.15 - Math.random() * 0.2, true);
        }

        //if frequency_start is less than 0.15, cutoff should be zero
        if (this.get_param("frequency_start") < 0.15) {
            this.set_param("min_frequency_relative_to_starting_frequency", 0, true);
            //frequency_slide should be between -.2 and -0.05
            this.set_param("frequency_slide", -0.1 - Math.random() * 0.1, true);
            console.log("adjusting for low frequency");
        }

        if (Math.random() < 0.5) {
            this.set_param("squareDuty", Math.random() * 0.5, true);
            this.set_param("dutySweep", Math.random() * 0.2, true);
        }
        else {
            this.set_param("squareDuty", 0.4 + Math.random() * 0.5, true);
            this.set_param("dutySweep", - Math.random() * 0.7, true);
        }

        this.set_param("sustainTime", 0.1 + Math.random() * 0.2, true);
        this.set_param("decayTime", Math.random() * 0.4, true);
        if (Math.random() < 0.5) this.set_param("sustainPunch", Math.random() * 0.3, true);

        if (Math.random() < 0.33) {
            this.set_param("flangerOffset", Math.random() * 0.2, true);
            this.set_param("flangerSweep", -Math.random() * 0.2, true);
        }

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
    }

    generate_explosion() {
        this.reset_params(true);
        if (Math.random() < 0.5) {
            this.set_param("waveType", 3, true);
        } else {
            this.set_param("waveType", 9, true);
        }

        if (Math.random() < 0.5) {
            this.set_param("frequency_start", 0.1 + Math.random() * 0.4, true);
            this.set_param("frequency_slide", -0.1 + Math.random() * 0.4, true);
        }
        else {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.7, true);
            this.set_param("frequency_slide", -0.2 - Math.random() * 0.2, true);
        }

        this.set_param("frequency_start", this.get_param("frequency_start") * this.get_param("frequency_start"), true);

        if (Math.random() < 0.2) this.set_param("frequency_slide", 0.0, true);
        if (Math.random() < 0.33) this.set_param("repeatSpeed", 0.3 + Math.random() * 0.5, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.3, true);
        this.set_param("decayTime", Math.random() * 0.5, true);
        this.set_param("sustainPunch", 0.2 + Math.random() * 0.6, true);

        if (Math.random() < 0.5) {
            this.set_param("flangerOffset", -0.3 + Math.random() * 0.9, true);
            this.set_param("flangerSweep", -Math.random() * 0.3, true);
        }

        if (Math.random() < 0.33) {
            this.set_param("pitch_jump_onset_percent", 0.6 + Math.random() * 0.3, true);
            this.set_param("pitch_jump_amount", 0.8 - Math.random() * 1.6, true);
        }
    }

    generate_powerup() {
        this.reset_params(true);

        if (Math.random() < 0.5) this.set_param("waveType", 1, true);
        else this.set_param("squareDuty", Math.random() * 0.6, true);

        if (Math.random() < 0.5) {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.3, true);
            this.set_param("frequency_slide", 0.1 + Math.random() * 0.4, true);
            this.set_param("repeatSpeed", 0.4 + Math.random() * 0.4, true);
        }
        else {
            this.set_param("frequency_start", 0.2 + Math.random() * 0.3, true);
            this.set_param("frequency_slide", 0.05 + Math.random() * 0.2, true);

            if (Math.random() < 0.5) {
                this.set_param("vibratoDepth", Math.random() * 0.7, true);
                this.set_param("vibratoSpeed", Math.random() * 0.6, true);
            }
        }

        this.set_param("sustainTime", Math.random() * 0.4, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.4, true);
    }

    generate_hit_hurt() {
        this.reset_params(true);
        this.set_param("waveType", this.select_random_wave_type("White","Bitnoise","Saw","Square","Voice"), true);
        if (this.get_param("waveType") == 0)
            this.set_param("squareDuty", Math.random() * 0.6);

        this.set_param("frequency_start", 0.2 + Math.random() * 0.6, true);
        this.set_param("frequency_slide", -0.3 - Math.random() * 0.4, true);

        this.set_param("sustainTime", Math.random() * 0.1, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.2, true);

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
    }

    generate_jump() {
        this.reset_params(true);

        this.set_param("waveType", this.select_random_wave_type("Square","Saw","FMSyn"), true);
        this.set_param("squareDuty", Math.random() * 0.6, true);
        this.set_param("frequency_start", 0.3 + Math.random() * 0.3, true);
        this.set_param("frequency_slide", 0.1 + Math.random() * 0.2, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.3, true);
        this.set_param("decayTime", 0.1 + Math.random() * 0.2, true);

        if (Math.random() < 0.5) this.set_param("hpFilterCutoff", Math.random() * 0.3, true);
        if (Math.random() < 0.5) this.set_param("lpFilterCutoff", 1.0 - Math.random() * 0.6, true);
    }

    generate_blip_select() {
        this.reset_params(true);
        this.set_param("waveType", this.select_random_wave_type("Square","Saw","FMSyn","Whistle"), true);
        if (this.get_param("waveType") == 0)
            this.set_param("squareDuty", Math.random() * 0.6, true);

        this.set_param("frequency_start", 0.2 + Math.random() * 0.4, true);

        this.set_param("sustainTime", 0.1 + Math.random() * 0.1, true);
        this.set_param("decayTime", Math.random() * 0.2, true);
        this.set_param("hpFilterCutoff", 0.1, true);
    }

    static #RandomizationPower =
        {
            attackTime: 4,
            sustainTime: 2,
            sustainPunch: 2,
            overtones: 3,
            overtoneFalloff: 2,
            vibratoDepth: 3,
            dutySweep: 3,
            flangerOffset: 3,
            flangerSweep: 3,
            lpFilterCutoff: 3,
            lpFilterSweep: 3,
            hpFilterCutoff: 5,
            hpFilterSweep: 5,
            bitCrush: 4,
            bitCrushSweep: 5,
            slide:4,
            frequency_acceleration:7,
            frequency_start:4
        }

    static #WaveTypeWeights =
        [
            1,//0:square
            1,//1:saw
            1,//2:sin
            1,//3:noise
            1,//4:triangle
            1,//5:buzz
            1,//6:tan
            1,//7:whistle
            1,//8:breaker
            1,//9:bitnoise
            1,//10:new 1
        ];

    static #WaveTypeIndices = {
        "Triangle":4,
        "Sin":2,
        "Square":0,
        "Saw":1,
        "Breaker":8,
        "Tan":6,
        "Whistle":7,
        "White":3,
        "Voice":11,
        "Bitnoise":9,
        "Rasp":5,
        "FMSyn":10
    }

    select_random_wave_type(...possible_wave_types){
        var wave_type_name = possible_wave_types[Math.floor(Math.random() * possible_wave_types.length)];
        var wave_type_index = Bfxr.#WaveTypeIndices[wave_type_name];
        return wave_type_index;
    }
    generate_random_centered_around_x(min,max,centre){
        //first decided if above or below centre
        if (Math.random() < 0.5){
            //above centre
            var r = Math.random();
            r = Math.pow(r, 2);
            return centre + r*(max-centre);
        }
        else{
            //below centre
            var r = Math.random();
            r = Math.pow(r, 2);
            return centre - r*(centre-min);
        }
    }

    randomize_params() {
        for (var param in this.params) {
            if (!this.locked_params[param]) {
                var min = this.param_min(param);
                var max = this.param_max(param);
                var default_val = this.param_default(param);
                var r = Math.random();
                if (param in Bfxr.#RandomizationPower)
                    r = Math.pow(r, Bfxr.#RandomizationPower[param]);
                var above = Math.random() < 0.5;
                if (min===default_val){
                    above=true;
                }
                if (max===default_val){
                    above=false;
                }
                if (above){
                    this.params[param] = default_val + (max - default_val) * r;
                } else {
                    this.params[param] = default_val - (default_val - min) * r;
                }
            }
        }

        if (!this.locked_params["waveType"]) {
            var count = 0;
            for (var i = 0; i < Bfxr.#WaveTypeWeights.length; i++) {
                count += Bfxr.#WaveTypeWeights[i];
            }
            r = Math.random() * count;
            for (i = 0; i < Bfxr.#WaveTypeWeights.length; i++) {
                r -= Bfxr.#WaveTypeWeights[i];
                if (r <= 0) {
                    this.set_param("waveType", i);
                    break;
                }
            }

        }

        if (Math.random() < 0.5)
            this.set_param("repeatSpeed", 0,true);


        this.set_param("min_frequency_relative_to_starting_frequency", 0,true);

        this.set_param("compressionAmount", 0,true);

        this.rectify_params();

    }

    mutate_params(){
        //with a small probability, mutate the waveType
        if (Math.random() < 0.1){
            var wave_count = Object.keys(Bfxr.#WaveTypeIndices).length;
            var random_wave_index_offset = Math.floor(Math.random() * (wave_count-1));
            var random_wave_index = (this.get_param("waveType") + random_wave_index_offset) % wave_count;
            this.set_param("waveType", random_wave_index, true);
            return;
        }
        super.mutate_params();
        this.rectify_params();
    }

    //tidies up bad parameters that might cause the sound to be inaudible/bad
    rectify_params(){
        //want startfrequency centered around 0.3, falling off quadratically
        var frequency_default = this.param_default("frequency_start");
        //set to 0.2 if waveType is voice (11)
        if (this.get_param("waveType") == 11){
            frequency_default = 0.22;
        }
        this.set_param("frequency_start", this.generate_random_centered_around_x(0,0.6,frequency_default),true);

        if ((!this.locked_params["sustainTime"]) && (!this.locked_params["decayTime"])) {
            if (this.get_param("attackTime") + this.get_param("sustainTime") + this.get_param("decayTime") < 0.2) {
                this.set_param("sustainTime", 0.2 + Math.random() * 0.3);
                this.set_param("decayTime", 0.2 + Math.random() * 0.3);
            }
        }
        //punch between 0 and 1, but square the random value so that smaller values are more likely
        var r = Math.random()*Math.random();
        this.set_param("sustainPunch", r*r, true);

        if ((this.get_param("frequency_start") > 0.7 && this.get_param("frequency_slide") > 0.2) || (this.get_param("frequency_start") < 0.2 && this.get_param("frequency_slide") < -0.05)) {
            this.set_param("frequency_slide", -this.get_param("frequency_slide"),true);
        }

        if (this.get_param("lpFilterCutoff") < 0.1 && this.get_param("lpFilterCutoffSweep") < 0) {
            this.set_param("lpFilterCutoffSweep", -this.get_param("lpFilterCutoffSweep")+0.2,true);
        }

        //if wavetype is not square, set duty values to default
        if (this.get_param("waveType") !== 0){
            this.set_param("squareDuty", this.param_default("squareDuty"),true);
            this.set_param("dutySweep", this.param_default("dutySweep"),true);
        } else {
            //when duty is 0, dutysweep can be anything between min and max
            //when duty is near 1, dutysweep should be <=0 80% of the time, and >=0 20% of the time
            var duty = this.get_param("squareDuty");
            var random_param = Math.random();
            if (duty>0.7 && random_param<0.5){
                this.set_param("dutySweep", -Math.random()*0.5,true);
                //this is just to stop the dutySweep from wiping out the sound when it gets too high (too regularly)
            }
        }
    }

    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/

    render() {
        // The legacy DSP adjusts envelope values while rendering; keep saved data intact.
        var dsp = new Bfxr_DSP({...this.params}, this);
        dsp.generate_sound();
        return dsp.buffer;
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }

    /*********************/
    /* MISCELLANEOUS     */
    /*********************/
    param_is_disabled(param_name){
        if (this.get_param("waveType") !== 0){//if not a square wave, disable squareDuty and dutySweep
            if (param_name == "squareDuty" || param_name == "dutySweep"){
                return true;
            }
        }
        if (param_name == "min_frequency_relative_to_starting_frequency"){
            //disable if frequency slide and frequency delta are both non-negative
            if (this.get_param("frequency_slide") >= 0 && this.get_param("frequency_acceleration") >= 0){
                return true;
            }
        }
        return false;
    }

}

// js/synths/Footsteppr.js
class Footsteppr extends SynthBase {

    name = "Footsteppr";
    version = "1.0.0"
    tooltip = "Bfxr is a wonderful physical simulation of footstep sounds, originally by Obiwannabe.";

    canvas_bg_logo = "img/logo_footsteppr.png";

    header_properties = ["waveType"];

    permalocked = ["masterVolume"];
    hide_params = ["masterVolume"];

    param_info = [
        [
            "Sound Volume",
            "Overall volume of the current sound.",
            "masterVolume",0.5,0,1
        ],
        {
            type: "BUTTONSELECT",

            name: "terrain",
            display_name: "Terrain",
            tooltip: "",

            default_value: 0,
            columns: 5,
            header: true,

            values: [
                [
                    "Snow",
                    "Traipsing around in the snow-blanketed forest.",
                    0
                ],
                [
                    "Grass",
                    "Dancing around the summer meadows.",
                    1
                ],
                [
                    "Dirt",
                    "The grass is all trampled away.",
                    2
                ],
                [
                    "Gravel",
                    "I hope you're not disrespecting anyone's grave!",
                    3
                ],
                [
                    "Wood",
                    "Fancy wooden floor - don't scratch it with your caperings.",
                    4
                ],
            ]
        },
        [
            "Heel",
            "How hard you strike the ground with your heel.",
            "heel",0.5,0,1
        ],
        [
            "Roll",
            "After making initial contact with the ground, how much you roll your foot to the side.",
            "roll",0.5,0,1
        ],
        [
            "Ball",
            "At the final part of your step, how much you dig the front of your foot into the ground.",
            "ball",0.5,0,1
        ],
        [
            "Swiftness",
            "How quick the step is.",
            "swiftness",0.5,0,1
        ],
    ];

    templates = [
        [
            "Randomize",
            "Talking your life into your hands... (only modifies unlocked parameters)",
            "randomize_params",
            "Random"
        ],
        [
            "Mutate",
            "Modify each unlocked parameter by a small wee amount... (only modifies unlocked parameters)",
            "mutate_params",
            "Mutant"
        ],
    ];

    /*********************/
    /* CONSTRUCTOR       */
    /*********************/

    constructor() {
        super();
        this.post_initialize();
    }

    /*********************/
    /* TEMPLATE FUNCTIONS  */
    /*********************/

    generate_pickup_coin() {
        return this.params;
    }

    /*********************/
    /* SOUND SYNTHESIS   */
    /*********************/

    render() {
        return Footsteppr_DSP.render(this.params);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }
}

// js/synths/Transfxr.js
class Transfxr extends SynthBase {
    name = 'Transfxr';
    version = '1.0.0';
    tooltip = 'Move between two sound states: set the start, the destination and the journey.';
    canvas_bg_logo = 'img/logo_transfxr.png';
    header_properties = ['waveType'];
    permalocked = ['masterVolume'];
    hide_params = ['masterVolume','waveTo'];
    static tweenfunctions = Transfxr_DSP.curves;
    static preset_families = typeof TRANSFXR_PRESET_FAMILIES === 'undefined' ? [] : TRANSFXR_PRESET_FAMILIES;

    static transitionParam(name, display_name, tooltip, start, end, curve = 'Linear') {
        return {type:'KNOB_TRANSITION', name, display_name, tooltip,
            default_value_l:start, default_value_r:end, min:0, max:1,
            default_tween:curve, curves: this.tweenfunctions.map(c => c[0])};
    }

    param_info = [
        ['Sound Volume', 'Overall volume of the current sound.', 'masterVolume', 0.5, 0, 1],
        {type:'BUTTONSELECT', name:'waveType', display_name:'', tooltip:'The oscillator beneath the changing sound.',
            default_value:0, columns:4, header:true,
            values:BfxrWaveforms.choices.map(([label,tip,id])=>[label,tip,
                ({2:0,4:1,1:2,0:3,8:4,6:5,7:6,3:7,11:8,9:9,5:10,10:11})[id]])},
        ['Duration', 'Time to travel along the curves, in seconds. Echo can ring out afterwards.', 'duration', 0.65, 0.05, 4],
        Transfxr.transitionParam('pitch', 'Pitch', 'Start and destination pitch, from 40 Hz to 5120 Hz. Equal spacing is equal musical intervals.', 0.48, 0.25, 'Ease Out'),
        Transfxr.transitionParam('tone', 'Filter', 'Low-pass cutoff: dark and muffled to bright and open.', 0.9, 0.45),
        Transfxr.transitionParam('vibrato', 'Wobble', 'Depth of an eight-cycle-per-second pitch wobble.', 0, 0.15, 'Ease In'),
        Transfxr.transitionParam('level', 'Level', 'Volume along the journey, before the attack and release fades.', 0.85, 0.45),
        ['Attack', 'Fade-in time in seconds, within the duration.', 'attack', 0.008, 0, 1],
        ['Release', 'Fade-out time in seconds, within the duration.', 'release', 0.18, 0, 1],
        ['Resonance', 'Emphasize the moving filter frequency.', 'resonance', 0.15, 0, 1],
        ['Echo', 'Repeating, fading reflections after the voice.', 'echo', 0.15, 0, 0.8],
        {type:'BUTTONSELECT',name:'waveTo',display_name:'Morph to',default_value:-1,columns:4,
            values:[["Don't morph waveform",'Keep the starting waveform.',-1],...BfxrWaveforms.choices.map(([label,tip,id])=>[label,tip,({2:0,4:1,1:2,0:3,8:4,6:5,7:6,3:7,11:8,9:9,5:10,10:11})[id]])]},
        Transfxr.transitionParam('morph','Morph','Blend from the starting waveform into the chosen destination.',0,1,'Smooth')
    ];

    // Original exact recipes remain available for saved examples and rendering tools.
    static examples = [
        {name:'Laser Zip', id:'laser_zip', tip:'A bright little bolt with a falling tail.',
            params:{waveType:2,duration:0.22,attack:0,release:0.14,resonance:0.32,echo:0.14,
                pitch:[0.82,0.22,'Ease Out'],tone:[0.95,0.25],level:[0.9,0.25]}},
        {name:'Bubble Drop', id:'bubble_drop', tip:'A plump, bouncing water droplet.',
            params:{duration:0.38,attack:0.003,release:0.26,echo:0.18,
                pitch:[0.29,0.68,'Bounce'],tone:[0.9,0.65],level:[0.95,0.1]}},
        {name:'Portal Bloom', id:'portal_bloom', tip:'A slow shimmering opening into somewhere else.',
            params:{waveType:2,duration:1.9,attack:0.5,release:0.65,resonance:0.55,echo:0.62,
                pitch:[0.18,0.5,'Smooth'],tone:[0.1,0.85,'Pulse'],waveTo:7,morph:[0.08,0.32,'Pulse'],
                vibrato:[0.03,0.65,'Ease In'],level:[0.45,0.95,'Pulse']}},
        {name:'Power Up', id:'power_up', tip:'Five rising steps, ready for the next level.',
            params:{waveType:3,duration:0.72,attack:0.01,release:0.16,resonance:0.12,echo:0.38,
                pitch:[0.35,0.64,'Steps'],tone:[0.55,0.95,'Ease In'],level:[0.7,0.9]}},
        {name:'Soft Landing', id:'soft_landing', tip:'A low, cushioned thump dissolving into dust.',
            params:{waveType:1,duration:0.58,attack:0.004,release:0.5,resonance:0.2,echo:0,
                pitch:[0.25,0.02,'Ease Out'],tone:[0.6,0.08,'Ease Out'],waveTo:7,morph:[0.3,0.6],level:[1,0]}},
        {name:'Clockwork Bird', id:'clockwork_bird', tip:'A tiny brass bird trying out its voice.',
            params:{waveType:1,duration:0.44,attack:0.012,release:0.12,resonance:0.3,echo:0.32,
                pitch:[0.62,0.85,'Triangle'],tone:[0.7,1],vibrato:[0.05,0.8,'Ease In'],level:[0.8,0.55]}},
        {name:'Ghost Signal', id:'ghost_signal', tip:'A distant transmission losing its shape.',
            params:{duration:1.45,attack:0.22,release:0.55,resonance:0.65,echo:0.65,
                pitch:[0.62,0.35,'Smooth'],tone:[0.75,0.3],waveTo:7,morph:[0,0.4,'Ease In'],
                vibrato:[0.9,0.05,'Ease Out'],level:[0.75,0.12]}},
        {name:'Airlock', id:'airlock', tip:'A resonant rush of air settling into silence.',
            params:{waveType:2,duration:1.15,attack:0.12,release:0.5,resonance:0.75,echo:0.12,
                pitch:[0.1,0.04],tone:[0.12,0.85,'Triangle'],waveTo:7,morph:[0.95,1],level:[0.7,0.95,'Pulse']}}
    ];

    templates = [
        ...(Transfxr.preset_families.length ? Transfxr.preset_families.map(p =>
            [p.name,p.tip,'generate_family_'+p.id,p.name.replace(/ /g,'')]) :
            Transfxr.examples.map(p => [p.name,p.tip,'generate_'+p.id,p.name.replace(/ /g,'')])),
        ['Timbral Morph','Generate a journey between two waveform characters.','generate_morph','Morph'],
        ['Randomize','Find a new journey; locked controls stay put.','randomize_params','Random'],
        ['Mutate','Nudge both endpoints of unlocked controls.','mutate_params','Mutant']
    ];

    constructor() {
        super();
        this.post_initialize();
        for (const example of Transfxr.examples) this['generate_'+example.id] = () => this.generate_example(example.id);
        for (const family of Transfxr.preset_families) this['generate_family_'+family.id] = () => this.generate_family(family.id);
    }

    apply_params(params, check_locked = false) {
        if(!params||typeof params!=='object')return;
        if(params.noise && typeof params.noise==='object' &&
            (params.waveTo===undefined || params.waveTo===-1) &&
            (params.noise.start>0 || params.noise.end>0)) {
            // Saved sounds from before waveform morphing used a separate white-noise blend.
            params={...params,waveTo:7,morph:params.noise};
        }
        if(['waveType','duration','pitch','tone','vibrato','level'].every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            const defaults=this.default_params();
            for(const key of ['waveTo','morph'])if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,defaults[key],check_locked);
        }
        // File/link input is data, not a guarantee of finite, in-range controls.
        for (const info of this.param_info) {
            const name = this.get_param_normalized(info).name;
            if (Object.prototype.hasOwnProperty.call(params, name)) this.set_param(name, params[name], check_locked);
        }
    }

    generate_example(id, vary = true) {
        const example = Transfxr.examples.find(p => p.id === id);
        this.reset_params(true);
        const shift = vary ? (Math.random() - 0.5) * 0.045 : 0;
        for (const [key, value] of Object.entries(example.params)) {
            if (Array.isArray(value)) {
                this.set_param(key, {start:value[0] + (key==='pitch'?shift:0),
                    end:value[1] + (key==='pitch'?shift:0),curve:value[2] || 'Linear'}, true);
            } else this.set_param(key, value, true);
        }
    }

    create_editor(tab,parent) { return new MorphEditor(tab,parent); }

    generate_morph() {
        this.create_random_template();
        this.set_param('waveTo',(this.params.waveType+1+Math.floor(Math.random()*11))%12,true);
        this.set_param('morph',{start:0,end:1,curve:['Smooth','Ease In','Ease Out','Pulse'][Math.floor(Math.random()*4)]},true);
        this.set_param('tone',{start:.8,end:.75+Math.random()*.25,curve:'Smooth'},true);
        this.set_param('duration',.5+Math.random()*1.2,true);
    }

    generate_family(id) {
        const family = Transfxr.preset_families.find(p => p.id === id);
        if (!family) throw new Error('Unknown Transfxr family: '+id);
        this.reset_params(true);
        this.apply_params(PresetFamily.sample(family), true);
    }

    create_random_template() {
        if (Transfxr.preset_families.length) {
            const family = Transfxr.preset_families[Math.floor(Math.random() * Transfxr.preset_families.length)];
            this.generate_family(family.id);
            return [family.name.replace(/ /g,''),this.params];
        }
        const example = Transfxr.examples[Math.floor(Math.random() * Transfxr.examples.length)];
        this.generate_example(example.id);
        return [example.name.replace(/ /g,''),this.params];
    }

    randomize_params() {
        super.randomize_params();
        this.set_param('duration', 0.15 + Math.random() * 1.65, true);
        this.set_param('attack', Math.random() * this.params.duration * 0.25, true);
        this.set_param('release', Math.random() * this.params.duration * 0.6, true);
        this.set_param('level', {start:0.4 + Math.random()*0.6,end:0.15 + Math.random()*0.75,curve:'Linear'}, true);
    }

    format_transition_value(name, value) {
        if (name === 'pitch') return Math.round(Transfxr_DSP.frequency(value)) + ' Hz';
        if (name === 'tone') {
            const hz = Transfxr_DSP.cutoff(value);
            return hz < 1000 ? Math.round(hz) + ' Hz' : (hz/1000).toFixed(1) + ' kHz';
        }
        return Math.round(value * 100) + '%';
    }

    render() {
        return Transfxr_DSP.render(this.params);
    }

    generate_sound() {
        if (this.sound) this.sound.stop();
        this.sound = RealizedSound.from_buffer(this.render());
        this.sound_params = JSON.stringify(this.params);
    }
}

class MorphEditor {
    constructor(tab,parent) {
        this.tab=tab;
        const row=document.createElement('label');row.className='morph-target';row.textContent='Morph to';
        this.select=document.createElement('select');this.select.setAttribute('aria-label','Morph to');
        for(const [label,tip,value] of tab.synth.get_param_info('waveTo').values){
            const option=document.createElement('option');option.value=value;option.textContent=label;option.title=tip;this.select.appendChild(option);
        }
        this.select.addEventListener('change',()=>{tab.synth.set_param('waveTo',+this.select.value);tab.parameter_changed();});
        this.select.addEventListener('keydown',event=>event.stopPropagation());
        row.appendChild(this.select);parent.appendChild(row);
        // Keep the curve with its destination, without changing the saved parameter schema.
        this.curveRow=document.getElementById(tab.name+'_graph_morph').closest('tr');
        const table=document.createElement('table');table.className='morph-curve';
        table.appendChild(this.curveRow);parent.appendChild(table);
        this.update();
    }
    update(){
        this.select.value=this.tab.synth.params.waveTo;
        this.curveRow.hidden=this.tab.synth.params.waveTo===-1;
    }
}

// js/synths/Clonkr.js
class Clonkr extends PresetSynth {
    name = 'Clonkr';
    canvas_bg_logo = 'img/logo_clonkr.png';
    tooltip = 'Knock, scrape, and rattle imaginary objects made of real-sounding materials.';
    static DSP = Clonkr_DSP;
    header_properties = ['material', 'action'];

    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'material', display_name:'Material', tooltip:'The resonances and decay of the object.',
            default_value:0, columns:5, header:true, values:[
                ['Wood','Dry, uneven wooden modes.',0], ['Glass','Clear, widely spaced ringing modes.',1],
                ['Metal','Dense, long-ringing inharmonic modes.',2], ['Ceramic','Brittle, short bell-like modes.',3],
                ['Rubber','Low, soft, heavily damped modes.',4]]},
        {type:'BUTTONSELECT', name:'action', display_name:'Contact', tooltip:'How the object is excited.',
            default_value:0, columns:3, header:true, values:[
                ['Hit','A single strike.',0], ['Scrape','Continuous rough contact.',1], ['Rattle','Uneven bouncing collisions.',2]]},
        ['Size','Small bright objects to large low objects.','size',0.5,0,1],
        ['Hollowness','Emphasize the hollow body resonance.','hollowness',0.35,0,1],
        ['Strike Hardness','A padded contact to a sharp, brittle strike.','hardness',0.65,0,1],
        ['Damping','How quickly the material absorbs its ringing.','damping',0.35,0,1],
        ['Duration','Resonance scale; also the contact time for scrapes and rattles.','duration',0.7,0.1,2]
    ];

    recipes = [
        {name:'Teacup', id:'teacup', tip:'Tap a small hollow china cup.',
            values:{material:3,action:0,size:[0.18,0.32],hollowness:[0.65,0.95],hardness:[0.55,0.8],damping:[0.1,0.32],duration:[0.45,0.9]}},
        {name:'Glass Ping', id:'glass_ping', tip:'A bright, delicate piece of glass.',
            values:{material:1,action:0,size:[0.05,0.23],hollowness:[0.25,0.65],hardness:[0.7,1],damping:[0.05,0.24],duration:[0.5,1.15]}},
        {name:'Wood Knock', id:'wood_knock', tip:'A dry knock on a wooden block or door.',
            values:{material:0,action:0,size:[0.36,0.68],hollowness:[0.25,0.7],hardness:[0.35,0.7],damping:[0.35,0.72],duration:[0.2,0.6]}},
        {name:'Dungeon Gate', id:'dungeon_gate', tip:'Heavy iron scraping and ringing in a stone passage.',
            values:{material:2,action:[1,2],size:[0.78,1],hollowness:[0.6,0.95],hardness:[0.35,0.65],damping:[0.16,0.38],duration:[1.2,2]}},
        {name:'Metal Clang', id:'metal_clang', tip:'Strike a resonant metal plate.',
            values:{material:2,action:0,size:[0.38,0.68],hollowness:[0.05,0.4],hardness:[0.65,1],damping:[0.05,0.3],duration:[0.7,1.5]}},
        {name:'Ceramic Crack', id:'ceramic_crack', tip:'Brittle pottery cracking into short rattling shards.',
            values:{material:3,action:2,size:[0.08,0.4],hollowness:[0.05,0.3],hardness:[0.8,1],damping:[0.68,0.95],duration:[0.12,0.32]}},
        {name:'Rubber Thud', id:'rubber_thud', tip:'A heavy cushioned bounce.',
            values:{material:4,action:0,size:[0.55,0.95],hollowness:[0.3,0.8],hardness:[0.08,0.35],damping:[0.3,0.7],duration:[0.35,0.8]}},
        {name:'Loose Bolts', id:'loose_bolts', tip:'A handful of small metal parts tumbling together.',
            values:{material:2,action:2,size:[0.18,0.4],hollowness:[0,0.25],hardness:[0.7,1],damping:[0.48,0.8],duration:[0.45,1]}},
        {name:'Dragged Crate', id:'dragged_crate', tip:'Rough wood scraping along the floor.',
            values:{material:0,action:1,size:[0.65,0.95],hollowness:[0.55,0.95],hardness:[0.4,0.8],damping:[0.5,0.85],duration:[0.65,1.6]}},
        {name:'Coin Drop', id:'coin_drop', tip:'A small coin bouncing and settling.',
            values:{material:2,action:2,size:[0.03,0.16],hollowness:[0,0.25],hardness:[0.8,1],damping:[0.3,0.6],duration:[0.22,0.52]}}
    ];

    constructor() { super(); this.initialize_presets(); }
}

// js/synths/Machinr.js
class Machinr extends PresetSynth {
    name = 'Machinr';
    canvas_bg_logo = 'img/logo_machinr.png';
    tooltip = 'Motors, gears, shutters and stubborn mechanisms. Each category builds a new machine.';
    static DSP = Machinr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'mechanism', display_name:'Mechanism', tooltip:'The moving parts inside the machine.',
            default_value:0, columns:4, values:[['Motor','An electric rotor and bearings.',0],['Gears','Meshing teeth and a strained winch.',1],
                ['Shutter','A fast spring, latch and winding motor.',2],['Clock','An alternating escapement.',3],
                ['Engine','Uneven combustion and exhaust.',4],['Servo','A small motor seeking a position.',5],
                ['Toy','A winding spring and chattering gears.',6],['Door','A heavy hinge, sliding body and closing latch.',7]]},
        ['Duration','Length of the complete movement, in seconds.','duration',1.8,0.12,6],
        ['Speed','Rotation rate or repetition speed of the moving parts.','speed',0.55,0,1],
        ['Load','Resistance against the mechanism: slower, strained and heavier.','load',0.25,0,1],
        ['Roughness','Worn bearings, friction and irregular running.','roughness',0.25,0,1],
        ['Gear Looseness','Loose parts add rattling and uneven tooth contacts.','looseness',0.2,0,1],
        ['Size','From tiny bright parts to a large, deep machine.','size',0.35,0,1],
        ['Start Time','Seconds taken to engage and reach working speed.','startTime',0.08,0,2],
        ['Stop Time','Seconds spent slowing down and stopping.','stopTime',0.16,0,2]
    ];
    recipes = [
        {name:'Tiny Motor',id:'tiny_motor',tip:'A fresh little electric motor spinning up.',values:{mechanism:0,duration:[0.6,1.8],speed:[0.65,0.95],load:[0.05,0.3],roughness:[0.02,0.2],looseness:[0.02,0.2],size:[0.03,0.25],startTime:[0.03,0.2],stopTime:[0.08,0.35]}},
        {name:'Rusty Winch',id:'rusty_winch',tip:'Slow, strained gears with a different creak each time.',values:{mechanism:1,duration:[1.4,3.7],speed:[0.12,0.4],load:[0.65,1],roughness:[0.6,0.95],looseness:[0.55,0.95],size:[0.55,0.9],startTime:[0.12,0.4],stopTime:[0.1,0.4]}},
        {name:'Camera Shutter',id:'camera_shutter',tip:'A quick spring release, double click and winding tail.',values:{mechanism:2,duration:[0.16,0.42],speed:[0.65,1],load:[0.05,0.35],roughness:[0.02,0.15],looseness:[0.1,0.4],size:[0.12,0.4],startTime:[0,0.004],stopTime:[0.02,0.07]}},
        {name:'Clockwork',id:'clockwork',tip:'A new tiny escapement, ticking against its gears.',values:{mechanism:3,duration:[1,2.8],speed:[0.1,0.48],load:[0.1,0.35],roughness:[0.02,0.18],looseness:[0.1,0.45],size:[0.08,0.45],startTime:[0,0.012],stopTime:[0.03,0.15]}},
        {name:'Engine Trouble',id:'engine_trouble',tip:'An engine coughing under uneven load.',values:{mechanism:4,duration:[1.5,3.5],speed:[0.18,0.55],load:[0.6,1],roughness:[0.7,1],looseness:[0.4,0.85],size:[0.6,1],startTime:[0.15,0.65],stopTime:[0.2,0.75]}},
        {name:'Servo',id:'servo',tip:'A high motor whine seeking a new position.',values:{mechanism:5,duration:[0.35,1.3],speed:[0.45,0.95],load:[0.1,0.55],roughness:[0.01,0.15],looseness:[0.01,0.2],size:[0.1,0.4],startTime:[0.008,0.06],stopTime:[0.025,0.12]}},
        {name:'Windup Toy',id:'windup_toy',tip:'A loose little spring-powered mechanism winding down.',values:{mechanism:6,duration:[1.2,3.2],speed:[0.55,0.95],load:[0.15,0.45],roughness:[0.2,0.55],looseness:[0.5,1],size:[0.02,0.32],startTime:[0.01,0.08],stopTime:[0.3,0.9]}},
        {name:'Heavy Door',id:'heavy_door',tip:'A deep hinge creak with a weighty closing latch.',values:{mechanism:7,duration:[1.1,3.2],speed:[0.1,0.45],load:[0.65,1],roughness:[0.5,0.95],looseness:[0.3,0.85],size:[0.75,1],startTime:[0.1,0.45],stopTime:[0.04,0.2]}}
    ];
    constructor() { super(); this.initialize_presets(); }
}

// js/synths/Jinglr.js
class Jinglr extends PresetSynth {
    name = 'Jinglr';
    canvas_bg_logo = 'img/logo_jinglr.png';
    tooltip = 'Little musical gestures for discoveries, victories, warnings and quiet moments.';
    static DSP = Jinglr_DSP;
    hide_params = ['masterVolume','phrase','instrument','instrumentSeed','seed'];
    header_properties = [];
    batching = false;

    param_info = [
        PresetSynth.common_params[0],
        ['Variation','A repeatable melody variation. Changing it makes a new unlocked phrase.','seed',50000/99999,0,1],
        ['Instrument seed','The five-digit character within this instrument family.','instrumentSeed',42731,0,99999],
        {type:'TEXT',name:'phrase',display_name:'Phrase',default_value:Jinglr_DSP.defaultPhrase,max_length:4096},
        {type:'BUTTONSELECT',name:'instrument',display_name:'Instrument',tooltip:'The voice playing each note.',
            default_value:0,columns:4,header:true,values:[['Pluck','A small string instrument.',0],['Bell','Sparkling, inharmonic chimes.',1],
                ['Chip','A bright arcade pulse.',2],['Flute','A soft breathy pipe.',3],
                ['Keys','Hammered, tine and electric keyboard tones.',4],['Reed','Woody and buzzy wind instruments.',5],
                ['FM','Glassy, metallic and rubbery digital voices.',6],['Strings','Soft bowed and shimmering ensemble tones.',7]]},
        {type:'BUTTONSELECT',name:'key',display_name:'Key',tooltip:'The root note of the phrase.',default_value:0,columns:6,
            values:['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'].map((name,index)=>[name,'Root note '+name,index])},
        {type:'BUTTONSELECT',name:'scale',display_name:'Scale',tooltip:'Notes stay within this scale when you change key.',default_value:0,columns:4,
            values:[['Major','Bright and settled.',0],['Minor','Somber and mysterious.',1],['Pentatonic','Five easygoing notes.',2],['Dorian','A gently hopeful minor scale.',3]]},
        {type:'BUTTONSELECT',name:'contour',display_name:'Contour',tooltip:'Choose a new shape for the unlocked phrase.',default_value:0,columns:5,
            values:[['Rise','Climb towards the last note.',0],['Fall','Settle downwards.',1],['Arch','Rise and return.',2],['Wander','A little melodic ramble.',3],['Call','Repeat a short call.',4]]},
        {type:'BUTTONSELECT',name:'rhythm',display_name:'Rhythm',tooltip:'Choose new note lengths for the unlocked phrase.',default_value:0,columns:4,
            values:[['Even','A steady sequence.',0],['Dotted','Long-short pairs.',1],['Skipping','Quick notes and pauses.',2],['Held','Room for each note to ring.',3]]},
        ['Notes','Number of notes in a newly generated phrase. Changing it makes a new unlocked phrase.','noteCount',4,2,12],
        ['Octave','The register of the root note.','octave',4,3,6],
        ['Tempo','Quarter-note beats per minute.','tempo',140,60,220],
        ['Swing','Delay every second note while preserving the length of each pair.','swing',0,0,0.6],
        ['Brightness','How much sparkle the instrument has.','brightness',0.55,0,1],
        ['Decay','How long each note holds and rings.','decay',0.45,0,1],
        ['Echo','Three soft musical repeats.','echo',0.12,0,0.8]
    ];

    recipes = [
        {name:'Confirm',id:'confirm',tip:'A quick, bright yes.',values:{instrument:[0,1,4,6],scale:0,contour:0,rhythm:0,noteCount:2,tempo:[200,220],octave:[4,5],brightness:[0.35,0.8],decay:[0.04,0.2],echo:0}},
        {name:'Message',id:'message',tip:'A small, soft arrival.',values:{instrument:[0,1,3,4],scale:2,contour:[0,4],rhythm:1,noteCount:2,tempo:[180,220],octave:[4,5],brightness:[0.15,0.55],decay:[0.06,0.24],echo:0}},
        {name:'Dismiss',id:'dismiss',tip:'A short downward reply.',values:{instrument:[0,2,4],scale:[0,2],contour:1,rhythm:0,noteCount:2,tempo:[195,220],octave:[3,4],brightness:[0.15,0.6],decay:[0.02,0.14],echo:0}},
        {name:'Denied',id:'denied',tip:'A compact, low refusal.',values:{instrument:[2,5,6],scale:1,contour:1,rhythm:1,noteCount:2,tempo:[200,220],octave:3,brightness:[0.2,0.6],decay:[0.01,0.12],echo:0}},
        {name:'Discovery',id:'discovery',tip:'An inquisitive rising sparkle.',values:{instrument:[0,1,4],scale:[0,2],key:[0,2,5,7,9],contour:0,rhythm:[0,1],noteCount:[4,7],tempo:[130,185],octave:[4,5],brightness:[0.5,0.9],decay:[0.3,0.65],echo:[0.1,0.3]}},
        {name:'Victory',id:'victory',tip:'A brisk, bright upward fanfare.',values:{instrument:[1,2,5],scale:0,key:[0,2,4,5,7],contour:0,rhythm:[0,1],noteCount:[5,9],tempo:[155,215],octave:[4,5],brightness:[0.7,1],decay:[0.35,0.6],echo:[0.1,0.3]}},
        {name:'Failure',id:'failure',tip:'A drooping little minor-key defeat.',values:{instrument:[0,2,7],scale:1,key:[0,2,5,7,9],contour:1,rhythm:[0,3],noteCount:[3,5],tempo:[80,120],octave:[3,4],brightness:[0.15,0.5],decay:[0.15,0.4],echo:[0,0.12]}},
        {name:'Secret',id:'secret',tip:'An elusive chime from somewhere nearby.',values:{instrument:[1,6],scale:[1,3],key:[1,3,6,8,10],contour:[2,3],rhythm:[1,2],noteCount:[4,7],tempo:[95,145],octave:[4,5],brightness:[0.4,0.85],decay:[0.55,0.85],echo:[0.3,0.55]}},
        {name:'Warning',id:'warning',tip:'An urgent repeated arcade call.',values:{instrument:[2,5],scale:1,key:[0,1,3,6,8],contour:4,rhythm:[0,2],noteCount:[4,8],tempo:[160,220],octave:[4,5],brightness:[0.7,1],decay:[0.05,0.25],echo:[0,0.08]}},
        {name:'Checkpoint',id:'checkpoint',tip:'A small reassuring arrival.',values:{instrument:[0,3,4],scale:[0,2],key:[0,2,5,7,9],contour:2,rhythm:0,noteCount:[3,5],tempo:[120,160],octave:[4,5],brightness:[0.3,0.65],decay:[0.35,0.65],echo:[0.05,0.2]}},
        {name:'Puzzle Solved',id:'puzzle_solved',tip:'A curious idea resolving into a bright finish.',values:{instrument:[0,1,6],scale:[0,2],key:[0,2,4,5,7,9],contour:0,rhythm:[1,2],noteCount:[6,10],tempo:[115,165],octave:[4,5],brightness:[0.45,0.8],decay:[0.45,0.7],echo:[0.18,0.35]}},
        {name:'Lullaby',id:'lullaby',tip:'A soft wandering tune with time to breathe.',values:{instrument:[0,3,7],scale:[0,2,3],key:[0,2,5,7,9],contour:[2,3],rhythm:3,noteCount:[4,7],tempo:[65,100],octave:[4,5],brightness:[0.05,0.35],decay:[0.65,0.95],echo:[0.12,0.3]}}
    ];

    constructor() { super(); this.initialize_presets(); }

    create_editor(tab,parent) { return new PhraseEditor(tab,parent); }

    static melody_seed(value) {
        return Math.round((Number.isFinite(value) ? SoundDSP.clamp(value,0,1) : 50000/99999)*99999)/99999;
    }

    set_param(name,value,checkLocked=false) {
        if (checkLocked && this.locked_param(name)) return;
        if (name==='phrase') value=JSON.stringify(Jinglr_DSP.phrase(value));
        if (name==='seed') value=Jinglr.melody_seed(value);
        if (['noteCount','octave','instrumentSeed'].includes(name)) value=Number.isFinite(value) ? Math.round(value) : value;
        super.set_param(name,value,checkLocked);
        if (!this.batching && ['noteCount','contour','rhythm','seed'].includes(name)) this.generate_phrase();
    }

    apply_params(params,checkLocked=false) {
        const previous=this.batching;
        this.batching=true;
        try {
            // Full snapshots from before instrument codes always start at the same voice.
            if (params && typeof params==='object' && ['phrase','seed','instrument'].every(name=>
                Object.prototype.hasOwnProperty.call(params,name)) &&
                !Object.prototype.hasOwnProperty.call(params,'instrumentSeed')) {
                this.set_param('instrumentSeed',42731,checkLocked);
            }
            super.apply_params(params,checkLocked);
        }
        finally { this.batching=previous; }
    }

    generate_recipe(id) {
        if (!this.recipes.some(recipe=>recipe.id===id)) return;
        this.reseed_sound(()=>super.generate_recipe(id));
    }

    reseed_sound(generate) {
        const locks=this.locked_params, batching=this.batching;
        const melody=this.params.seed, voice=this.params.instrumentSeed, phrase=this.params.phrase;
        // Presets replace the whole cue, including seeds held by the retired lock buttons.
        this.locked_params={...locks,phrase:false,seed:false,instrument:false,instrumentSeed:false};
        this.batching=true;
        try {
            generate();
            if (this.params.seed===melody) this.set_param('seed',((Math.round(melody*99999)+1)%100000)/99999);
            if (this.params.instrumentSeed===voice) this.set_param('instrumentSeed',(voice+1)%100000);
            this.generate_phrase();
            // Short two-note cues have few shapes; avoid immediately repeating one.
            for(let attempt=0;this.params.phrase===phrase && attempt<32;attempt++) {
                this.set_param('seed',((Math.round(this.params.seed*99999)+1)%100000)/99999);
                this.generate_phrase();
            }
        } finally {
            this.locked_params=locks;
            this.batching=batching;
        }
    }

    after_recipe() { this.generate_phrase(); this.generate_instrument(this.params.instrument); }

    generate_instrument(type) {
        this.set_param('instrument',type,true);
        // A repeat press always makes a different character, including under a fixed RNG.
        const step=1+Math.floor(Math.random()*99999);
        this.set_param('instrumentSeed',(this.params.instrumentSeed+step)%100000,true);
    }

    generate_phrase(freshSeed=false) {
        if (this.locked_param('phrase')) return;
        if (freshSeed) {
            const code=Math.round(this.params.seed*99999);
            const step=1+Math.floor(Math.random()*99999);
            super.set_param('seed',((code+step)%100000)/99999,true);
        }
        this.set_param('phrase',this.compose_phrase(),true);
    }

    melody_matches_seed() { return this.params.phrase===this.compose_phrase(); }

    compose_phrase(params=this.params) {
        const p=params, random=SoundDSP.rng(Jinglr.melody_seed(p.seed)), count=Math.round(p.noteCount);
        const span=4+Math.floor(random()*5), offset=Math.floor(random()*3)-1;
        const rhythms=[[0.5],[0.75,0.25],[0.25,0.5,0.25,0.75],[1,0.5,1,1.5]];
        let wander=offset;
        const notes=Array.from({length:count},(_,index)=>{
            const position=index/Math.max(1,count-1);
            const jitter=index===0 || index===count-1 ? 0 : Math.floor(random()*3)-1;
            let degree;
            switch (p.contour) {
                case 1: degree=offset+Math.round(span*(1-position))+jitter; break;
                case 2: degree=offset+Math.round(span*Math.sin(position*Math.PI))+jitter; break;
                case 3: wander+=Math.floor(random()*5)-2; degree=wander; break;
                case 4: degree=offset+(index%2 ? 3+Math.floor(random()*3) : 0); break;
                default: degree=offset+Math.round(span*position)+jitter;
            }
            let beats=rhythms[p.rhythm][index%rhythms[p.rhythm].length];
            if (index===count-1) beats=p.rhythm===3 ? 2 : 1;
            const rest=p.rhythm===2 && index>0 && index<count-1 && random()<0.18;
            return {degree:rest ? null : degree,beats};
        });
        return JSON.stringify(Jinglr_DSP.phrase(JSON.stringify(notes)));
    }

    randomize_params() {
        this.reseed_sound(()=>super.randomize_params());
    }

    mutate_params() {
        // A mutation gets a new visible code, so the resulting melody can be reconstructed.
        this.batching=true;
        try {
            super.mutate_params();
            const step=1+Math.floor(Math.random()*4999);
            const code=Math.round(this.params.seed*99999);
            const direction=Math.random()<0.5 ? -1 : 1;
            this.set_param('seed',((code+direction*step+100000)%100000)/99999,true);
        }
        finally { this.batching=false; }
        this.generate_phrase();
    }
}

// js/synths/Squishr.js
class Squishr extends PresetSynth {
    name = 'Squishr';
    canvas_bg_logo = 'img/logo_squishr.png';
    tooltip = 'Slime, bubbles, suction, and springy goo: tactile sounds from soft and liquid things.';
    static DSP = Squishr_DSP;
    header_properties = ['texture'];

    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'texture', display_name:'Texture', tooltip:'The liquid or soft-body gesture.',
            default_value:0, columns:3, header:true, values:[
                ['Slime','Sticky noise with scattered little squelches.',0], ['Bubbles','Rounded rising bubble resonances.',1],
                ['Suction','Pulling pressure followed by a release pop.',2], ['Splat','A noisy impact and scattered droplets.',3],
                ['Gulp','Repeated pairs of descending liquid resonances.',4], ['Spring','Stretchy, bouncing jelly oscillations.',5]]},
        ['Viscosity','Thin, bright liquid to thick, muffled goo.','viscosity',0.6,0,1],
        ['Stretch','Length and wobble of the soft-body deformation.','stretch',0.4,0,1],
        ['Pressure','Force, bubble activity, and pitch movement.','pressure',0.6,0,1],
        ['Wetness','Dry soft-body motion to prominent wet bubbles.','wetness',0.75,0,1],
        ['Bubble Size','Tiny high droplets to large, low liquid cavities.','bubbleSize',0.55,0,1],
        ['Duration','Length of the gesture in seconds.','duration',0.65,0.1,3]
    ];

    recipes = [
        {name:'Slime Step', id:'slime_step', tip:'A sticky footstep through a puddle of goo.',
            values:{texture:0,viscosity:[0.65,0.95],stretch:[0.25,0.6],pressure:[0.5,0.85],wetness:[0.65,1],bubbleSize:[0.55,0.85],duration:[0.28,0.55]}},
        {name:'Bubble Pop', id:'bubble_pop', tip:'A small rounded bubble bursting.',
            values:{texture:1,viscosity:[0.25,0.55],stretch:[0.02,0.25],pressure:[0.5,0.9],wetness:[0.8,1],bubbleSize:[0.15,0.4],duration:[0.1,0.2]}},
        {name:'Suction Cup', id:'suction_cup', tip:'Stretch the seal, then pop it free.',
            values:{texture:2,viscosity:[0.55,0.9],stretch:[0.55,0.95],pressure:[0.55,0.9],wetness:[0.4,0.8],bubbleSize:[0.45,0.7],duration:[0.35,0.8]}},
        {name:'Wet Splat', id:'wet_splat', tip:'A wet impact spraying small droplets.',
            values:{texture:3,viscosity:[0.1,0.4],stretch:[0.02,0.25],pressure:[0.75,1],wetness:[0.75,1],bubbleSize:[0.3,0.65],duration:[0.18,0.4]}},
        {name:'Gulp', id:'gulp', tip:'A low, hollow swallow of liquid.',
            values:{texture:4,viscosity:[0.3,0.6],stretch:[0.2,0.55],pressure:[0.35,0.65],wetness:[0.8,1],bubbleSize:[0.55,0.85],duration:[0.2,0.45]}},
        {name:'Springy Goo', id:'springy_goo', tip:'Elastic slime springing back into shape.',
            values:{texture:5,viscosity:[0.5,0.85],stretch:[0.75,1],pressure:[0.45,0.85],wetness:[0.25,0.6],bubbleSize:[0.4,0.7],duration:[0.45,0.95]}},
        {name:'Bubbling Potion', id:'bubbling_potion', tip:'An active cauldron of uneven rounded bubbles.',
            values:{texture:1,viscosity:[0.5,0.85],stretch:[0.2,0.65],pressure:[0.65,1],wetness:[0.8,1],bubbleSize:[0.35,0.8],duration:[1.4,2.7]}},
        {name:'Mud Pull', id:'mud_pull', tip:'Slowly pull something out of thick, sticky mud.',
            values:{texture:2,viscosity:[0.85,1],stretch:[0.7,1],pressure:[0.3,0.65],wetness:[0.35,0.7],bubbleSize:[0.75,1],duration:[0.9,1.8]}},
        {name:'Water Drop', id:'water_drop', tip:'A light high droplet falling into water.',
            values:{texture:1,viscosity:[0.02,0.25],stretch:[0.02,0.15],pressure:[0.15,0.45],wetness:[0.85,1],bubbleSize:[0.02,0.25],duration:[0.1,0.18]}},
        {name:'Jelly Wobble', id:'jelly_wobble', tip:'A large soft jelly shaking from side to side.',
            values:{texture:5,viscosity:[0.75,1],stretch:[0.6,0.95],pressure:[0.2,0.5],wetness:[0.05,0.3],bubbleSize:[0.7,1],duration:[0.8,1.5]}}
    ];

    constructor() { super(); this.initialize_presets(); }
}

// js/synths/Mixr.js
class Mixr extends PresetSynth {
    name = 'Mixr';
    tooltip = 'Two sounds together.';
    canvas_bg_logo = "img/logo_mixr.png";
    static DSP = Mixr_DSP;
    hide_params = ['masterVolume', 'seed', 'sources'];
    param_info = [
        ...PresetSynth.common_params,
        ['Balance', 'Balance between the two sounds.', 'balance', 0.5, 0, 1],
        {type:'TEXT', name:'sources', default_value:'[]', max_length:60000}
    ];
    recipes = [

        //GOOD
        {id:'clockwork_familiar',name:'Clockwork Aviary',pair:['Machinr','Birdr'],balance:[0.31,0.49],tip:'Machinr × Birdr.'},

        //OK
        {id:'crystal_prize',name:'Treasure Box',pair:['Jinglr','Clonkr'],balance:[0.5,0.68],tip:'Jinglr × Clonkr.'},
        {id:'cyber_bird',name:'Cyber Bird',pair:['Birdr','Bfxr'],balance:[0.37,0.55],tip:'Birdr × Bfxr.'},
        {id:'goo_machine',name:'Wetware',pair:['Squishr','Machinr'],balance:[0.44,0.62],tip:'Squishr × Machinr.'},
        {id:'alien_beacon',name:'Alien Broadcast',pair:['Signlr','Choirr'],balance:[0.44,0.62],tip:'Signlr × Choirr.'},

        {id:'garden_lute',name:'Garden Lute',pair:['Pluckr','Crittr'],balance:[0.11,0.29],tip:'Pluckr × Crittr.'},
        {id:'reality_error',name:'Reality Error',pair:['Riftr','Glitchr'],balance:[0.37,0.55],tip:'Sonar × Glitches.'},
        {id:'soft_landing',name:'Goo Collision',pair:['Bouncr','Squishr'],balance:[0.33,0.51],tip:'Bonks × Squishy.'},

        {id:'spark_impact',name:'Live Wire',pair:['Clonkr','Zappr'],balance:[0.52,0.7],tip:'Clonkr × Zappr.'},
        {id:'shockwave',name:'Shockwaves',pair:['Boomr','Breathr'],balance:[0.2,0.5],tip:'Boomr × Breathr.'},
        {id:'haunted_hardware',name:'Brain Zaps',pair:['Clonkr','Glitchr'],balance:[0.5,0.68],tip:'Clonkr × Glitchr.'},


        //BAD

        {id:'haunted',name:'Otherworld',pair:['Choirr','Riftr'],balance:[0.5,0.68],tip:'Choirr × Riftr.'},
        {id:'spell_hit',name:'Shatterstorm',pair:['Whooshr','Fractr'],balance:[0.57,0.75],tip:'Whooshr × Fractr.'},
        {id:'heavy_magic',name:'Thunderworks',pair:['Boomr','Zappr'],balance:[0.26,0.44],tip:'Boomr × Zappr.'},
        {id:'phase_step',name:'Phase Shift',pair:['Whooshr','Riftr'],balance:[0.38,0.56],tip:'Whooshr × Riftr.'},
        {id:'hatchling',name:'Monster Hatchery',pair:['Fractr','Crittr'],balance:[0.21,0.39],tip:'Fractr × Crittr.'},
        {id:'sacred_treasure',name:'Arcane Reward',pair:['Jinglr','Choirr'],balance:[0.43,0.61],tip:'Jinglr × Choirr.'},
        {id:'pocket_rattle',name:'Pocket Rattle',pair:['Rustlr','Clonkr'],balance:[0.12,0.3],tip:'Rustlr × Clonkr.'},
        {id:'demolition',name:'Demolition',pair:['Fractr','Boomr'],balance:[0.37,0.55],tip:'Fractr × Boomr.'}
    ].map(recipe => ({...recipe, tip:recipe.pair.map(synth_display_name).join(' × ')+'.', values:{balance:recipe.balance}}));
    constructor() { super(); this.initialize_presets(); }
    create_editor(tab,parent) { return new MixEditor(tab,parent); }
    create_random_template() { return super.create_random_template(); }
    get_sources() { return JSON.parse(this.params.sources); }

    static sources() {
        return [typeof Bfxr === 'undefined' ? null : Bfxr,
            typeof Footsteppr === 'undefined' ? null : Footsteppr,
            typeof Transfxr === 'undefined' ? null : Transfxr,
            typeof Clonkr === 'undefined' ? null : Clonkr,
            typeof Machinr === 'undefined' ? null : Machinr,
            typeof Jinglr === 'undefined' ? null : Jinglr,
            typeof Squishr === 'undefined' ? null : Squishr,
            typeof Crittr === 'undefined' ? null : Crittr,
            typeof Birdr === 'undefined' ? null : Birdr,
            typeof Signlr === 'undefined' ? null : Signlr,
            typeof Fractr === 'undefined' ? null : Fractr,
            typeof Riftr === 'undefined' ? null : Riftr,
            typeof Swarmr === 'undefined' ? null : Swarmr,
            typeof Rustlr === 'undefined' ? null : Rustlr,
            typeof Boomr === 'undefined' ? null : Boomr,
            typeof Zappr === 'undefined' ? null : Zappr,
            typeof Whooshr === 'undefined' ? null : Whooshr,
            typeof Bouncr === 'undefined' ? null : Bouncr,
            typeof Breathr === 'undefined' ? null : Breathr,
            typeof Choirr === 'undefined' ? null : Choirr,
            typeof Pluckr === 'undefined' ? null : Pluckr,
            typeof Glitchr === 'undefined' ? null : Glitchr].filter(Boolean);
    }
    static source(name) { const Constructor = this.sources().find(c => c.name === name); return Constructor ? new Constructor() : null; }

    static sanitize_source(synth, params) {
        // Older synths' apply_params accepts arbitrary keys; validate each known control here.
        // Apply editable scores last: generator controls can otherwise replace saved notes.
        const controls = synth.param_info.map(info => synth.get_param_normalized(info));
        controls.sort((a,b) => Number(a.type === 'TEXT') - Number(b.type === 'TEXT'));
        const known={};
        for(const info of controls)if(params&&Object.prototype.hasOwnProperty.call(params,info.name))known[info.name]=params[info.name];
        // Specialized engines filter their own input, and migrations may need former controls.
        // The legacy base setter accepts arbitrary keys, so only give it known controls.
        synth.apply_params(synth.apply_params === SynthBase.prototype.apply_params ? known : params);
        const migrated={...synth.params};
        synth.params=synth.default_params();
        for(const info of controls)synth.set_param(info.name,migrated[info.name]);
        return JSON.parse(JSON.stringify(synth.params));
    }

    static render_source(source, seed = 0.5) {
        const synth = this.source(source.synth);
        if (!synth) return new Float32Array(1);
        this.sanitize_source(synth,source.params);
        const originalRandom = Math.random;
        Math.random = SoundDSP.rng(seed);
        try {
            return synth.render();
        } finally { Math.random = originalRandom; }
    }

    static templates_for(synth) {
        if (!synth) return [];
        return synth.templates.filter(t => typeof synth[t[2]] === 'function' &&
            (t[2].startsWith('generate_') || (synth.name === 'Footsteppr' && t[2] === 'randomize_params')));
    }
    static generators() {
        return Mixr.sources().flatMap(Constructor => {
            const synth=new Constructor();
            return this.templates_for(synth).map(([name,tip,generator]) =>
                ({synth:synth.name, family:synth_display_name(synth.name), name, tip, generator}));
        });
    }
    static generated_source(name,generator,previousGenerator) {
        const synth=Mixr.source(name);
        const templates=this.templates_for(synth);
        let template;
        if(generator==='*'){
            const candidates=templates.length>1 ? templates.filter(t=>t[2]!==previousGenerator) : templates;
            template=candidates[Math.floor(Math.random()*candidates.length)];
        } else template=templates.find(t=>t[2]===generator);
        if(!template)return null;
        synth[template[2]]();
        const source={synth:synth.name,name:template[0],generator,params:synth.params,renderSeed:Math.random()};
        if(generator==='*')source.selectedGenerator=template[2];
        return source;
    }
    set_param(name,value,checkLocked=false) {
        if (name !== 'sources') return super.set_param(name,value,checkLocked);
        if (checkLocked && this.locked_param(name)) return;
        let sources;
        try { sources = typeof value === 'string' ? JSON.parse(value.slice(0,60000)) : value; } catch { sources = []; }
        const clean = (Array.isArray(sources) ? sources : []).slice(0,2).map(source => {
            const synth = source && Mixr.source(source.synth);
            if (!synth) return null;
            const entry={synth:synth.name, name:typeof source.name === 'string' ? source.name.slice(0,60) : synth.name,
                params:Mixr.sanitize_source(synth,source.params)};
            const templates=Mixr.templates_for(synth);
            if(source.generator==='*' && templates.length){
                entry.generator='*';
                if(templates.some(t=>t[2]===source.selectedGenerator))entry.selectedGenerator=source.selectedGenerator;
            } else if(templates.some(t=>t[2]===source.generator))entry.generator=source.generator;
            if(Number.isFinite(source.renderSeed))entry.renderSeed=SoundDSP.clamp(source.renderSeed,0,1);
            return entry;
        });
        this.params.sources = JSON.stringify(clean);
        this.sound_params = null;
    }
    set_source(slot,synth,name) {
        if (slot!==0 && slot!==1) return false;
        if (synth && synth.name === 'Mixr') return false;
        const sources=this.get_sources();
        while(sources.length<=slot)sources.push(null);
        sources[slot]=synth ? {synth:synth.name,name:name||synth.name,params:synth.params} : null;
        this.set_param('sources',sources);
        return true;
    }
    set_generator(slot,name,generator) {
        if(slot!==0 && slot!==1)return false;
        const sources=this.get_sources();
        const current=sources[slot];
        const previous=current && current.synth===name ? current.selectedGenerator || current.generator : undefined;
        const next=Mixr.generated_source(name,generator,previous);
        if(!next)return false;
        while(sources.length<=slot)sources.push(null);
        sources[slot]=next;
        this.set_param('sources',sources);
        return true;
    }
    regenerate_source(slot) {
        if(this.locked_param('sources'))return false;
        const current=this.get_sources()[slot];
        return current && current.generator ? this.set_generator(slot,current.synth,current.generator) : false;
    }
    regenerate_both() {
        if(this.locked_param('sources'))return;
        const sources=this.get_sources().map(current=>current && current.generator
            ? Mixr.generated_source(current.synth,current.generator,current.selectedGenerator) || current : current);
        this.set_param('sources',sources);
    }
    after_recipe(recipe) {
        if(this.locked_param('sources'))return;
        const sources=recipe.pair.map(name=>{
            const source=Mixr.generated_source(name,'*');
            if(!source)throw new Error('Unknown Mixr instrument: '+name);
            return source;
        });
        this.set_param('sources',sources);
    }
    randomize_params() { this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id); }
    mutate_params() {
        this.set_param('balance',this.params.balance+(Math.random()-.5)*.15,true);
        if(this.locked_param('sources'))return;
        const sources=this.get_sources().map(current=>{
            if(!current)return null;
            const source=Mixr.source(current.synth);
            source.apply_params(current.params);source.mutate_params();
            return {...current,params:source.params};
        });
        this.set_param('sources',sources);
    }
}

// js/synths/Crittr.js
class Crittr extends PresetSynth {
    name = 'Crittr';
    canvas_bg_logo = 'img/logo_crittr.png';
    tooltip = 'Nonverbal beasts, tiny companions and impossible wildlife.';
    static DSP = Crittr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'voice',display_name:'Anatomy',tooltip:'The source and throat shape of the creature.',
            default_value:0,columns:3,values:[['Throat','A warm, pulsing throat.',0],['Beak','A sharp, ringing chirp.',1],
                ['Gills','A hollow, bubbling voice.',2],['Chitin','A thin, buzzing stridulation.',3],
                ['Spirit','A soft, airy singing call.',4],['Clockwork','A metallic artificial throat.',5],['Dog','A chesty bark with a fast breath attack.',6],
                ['Cat','A voiced meow with a closing mouth.',7]]},
        ['Duration','Length of the complete call, in seconds.','duration',1.2,0.15,5],
        ['Pitch','The vibration rate of the creature\'s voice.','pitch',0.45,0,1],
        ['Throat Size','Small throats ring high; large throats resonate deeply.','size',0.45,0,1],
        ['Evolution','How far the throat opens and changes during each call.','morph',0.45,0,1],
        ['Calls','Number of separate vocal gestures.','calls',2,1,12],
        ['Call Gap','The portion of each gesture left for a pause.','gap',0.2,0,0.85],
        ['Pitch Bend','Falling grunts to rising yelps within each gesture.','contour',0.25,-1,1],
        ['Growl','Adds slower vocal folds below the main pitch.','growl',0.2,0,1],
        ['Breath','Air and rasp passing through the throat.','breath',0.15,0,1],
        ['Flutter','From a steady voice to rapid trills and trembling.','flutter',0.2,0,1]
    ];
    recipes = [
        {name:'Woof',id:'woof',tip:'A short bark, from a small yap to a chesty woof.',values:{voice:6,duration:[0.23,0.65],pitch:[0.18,0.43],size:[0.4,0.85],morph:[0.45,0.85],calls:1,gap:[0.06,0.18],contour:[-0.7,-0.25],growl:[0.18,0.5],breath:[0.14,0.35],flutter:[0.01,0.13]}},
        {name:'Meow',id:'meow',tip:'A rising, nasal meow relaxing into a rounded vowel.',values:{voice:7,duration:[0.35,0.95],pitch:[0.48,0.66],size:[0.24,0.52],morph:[0.65,1],calls:1,gap:[0.03,0.14],contour:[-0.35,0.1],growl:[0.01,0.12],breath:[0.01,0.09],flutter:[0.02,0.13]}},
        {name:'Tiny Dragon',id:'tiny_dragon',tip:'A little chirrup with a smoky throat.',values:{voice:1,duration:[0.45,1.2],pitch:[0.53,0.76],size:[0.1,0.35],morph:[0.45,0.95],calls:[1,3],gap:[0.16,0.36],contour:[-0.75,0.5],growl:[0.1,0.35],breath:[0.08,0.3],flutter:[0.04,0.2]}},
        {name:'Cave Beast',id:'cave_beast',tip:'A huge, uneven rumble from the dark.',values:{voice:0,duration:[1.1,2.9],pitch:[0.04,0.26],size:[0.7,1],morph:[0.5,1],calls:[1,2],gap:[0.05,0.25],contour:[-0.55,0.1],growl:[0.65,1],breath:[0.18,0.5],flutter:[0.08,0.3]}},
        {name:'Alien Purr',id:'alien_purr',tip:'A small contented creature with too many vocal folds.',values:{voice:2,duration:[1,2.4],pitch:[0.26,0.49],size:[0.25,0.65],morph:[0.2,0.55],calls:[1,3],gap:[0.02,0.16],contour:[-0.15,0.15],growl:[0.4,0.8],breath:[0.02,0.16],flutter:[0.65,0.95]}},
        {name:'Insect Call',id:'insect_call',tip:'A bright wing rasp in short phrases.',values:{voice:3,duration:[0.6,1.9],pitch:[0.7,0.94],size:[0.02,0.26],morph:[0.05,0.4],calls:[3,8],gap:[0.25,0.65],contour:[-0.12,0.17],growl:[0,0.05],breath:[0.1,0.3],flutter:[0.6,1]}},
        {name:'Ghost Whale',id:'ghost_whale',tip:'A long, hollow voice rising out of the deep.',values:{voice:4,duration:[2.3,4.5],pitch:[0.22,0.43],size:[0.68,1],morph:[0.65,1],calls:[1,2],gap:[0.02,0.15],contour:[0.45,0.95],growl:[0.12,0.4],breath:[0.12,0.32],flutter:[0.03,0.2]}},
        {name:'Clockwork Pet',id:'clockwork_pet',tip:'An eager little mechanical companion.',values:{voice:5,duration:[0.4,1.25],pitch:[0.45,0.72],size:[0.12,0.45],morph:[0.2,0.7],calls:[2,5],gap:[0.15,0.4],contour:[0.2,0.8],growl:[0.03,0.18],breath:[0,0.09],flutter:[0.12,0.45]}},
        {name:'Forest Spirit',id:'forest_spirit',tip:'A breathy, flickering woodland call.',values:{voice:4,duration:[0.9,2.3],pitch:[0.48,0.77],size:[0.2,0.5],morph:[0.4,0.85],calls:[2,4],gap:[0.16,0.4],contour:[-0.3,0.5],growl:[0.02,0.18],breath:[0.35,0.7],flutter:[0.25,0.6]}},
        {name:'Angry Blob',id:'angry_blob',tip:'An indignant, rubbery bubbling protest.',values:{voice:2,duration:[0.45,1.4],pitch:[0.14,0.38],size:[0.45,0.85],morph:[0.65,1],calls:[2,5],gap:[0.15,0.35],contour:[-0.85,-0.3],growl:[0.5,0.9],breath:[0.03,0.18],flutter:[0.15,0.5]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    randomize_params() {
        this.create_random_template();
        // Randomize is a one-shot explorer; longer recipe buttons and manual edits remain available.
        if (this.params.duration>1.5) this.set_param('duration',0.55+Math.random()*0.85,true);
    }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='calls' && !(checkLocked && this.locked_params[name])) {
            this.params.calls=Math.round(this.params.calls);
        }
    }
}

// js/synths/Birdr.js
class Birdr extends PresetSynth {
    name = 'Birdr';
    canvas_bg_logo = 'img/logo_birdr.png';
    tooltip = 'Birdsong, chirps, trills and wild calls in short phrases.';
    static DSP = Birdr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'voice',display_name:'Voice',tooltip:'The way the syrinx and beak shape the call.',default_value:0,columns:3,
            values:[['Whistle','A clear, single-voiced song.',0],['Twin','Two interacting sides of the syrinx.',1],
                ['Reed','A bright, nasal squawk.',2],['Rasp','A rough, throaty caw.',3],['Hoot','A rounded, hollow hoot.',4]]},
        ['Duration','Seconds for the complete phrase.','duration',0.8,0.15,5],
        ['Pitch','The pitch of the bird, from low hoots to tiny chirps.','pitch',0.58,0,1],
        ['Syllables','Number of separate calls in the phrase.','syllables',3,1,16],
        ['Gap','Breathing space between syllables.','gap',0.3,0,0.85],
        ['Sweep','A falling or rising pitch sweep within each syllable.','sweep',-0.3,-1,1],
        ['Arch','An upward or downward curve through each syllable.','arch',0.45,-1,1],
        ['Trill','Depth of rapid pitch and breath pulses.','trill',0.15,0,1],
        ['Trill Rate','Speed of the trill inside each syllable.','trill_rate',0.4,0,1],
        ['Duet','Amount of the second voice; Twin makes it interact with the first.','duet',0.1,0,1],
        ['Rasp','Uneven vocal fold vibration and rough overtones.','rasp',0.04,0,1],
        ['Breath','Air flowing past the beak.','breath',0.03,0,1],
        ['Rhythm','Uneven timing of the syllables.','rhythm',0.12,0,1],
        ['Phrase','Pitch and articulation changes across the phrase.','variation',0.25,0,1]
    ];
    recipes = [
        {name:'Chirp',id:'chirp',tip:'One quick, bright call.',values:{voice:0,duration:[0.15,0.32],pitch:[0.57,0.78],syllables:1,gap:[0.08,0.2],sweep:[-0.75,0.65],arch:[0.25,0.9],trill:[0,0.1],duet:[0,0.08],rasp:[0,0.05],breath:[0.01,0.06]}},
        {name:'Sparrow',id:'sparrow',tip:'A handful of short, chattering chirps.',values:{voice:1,duration:[0.45,1],pitch:[0.6,0.77],syllables:[3,6],gap:[0.35,0.58],sweep:[-0.6,-0.1],arch:[0.3,0.8],trill:[0.05,0.2],duet:[0.1,0.3],rasp:[0.08,0.25],rhythm:[0.25,0.6],variation:[0.1,0.35]}},
        {name:'Songbird',id:'songbird',tip:'A lilting phrase with a repeated contour.',values:{voice:0,duration:[0.7,1.5],pitch:[0.45,0.67],syllables:[3,6],gap:[0.2,0.4],sweep:[-0.2,0.45],arch:[0.35,0.8],trill:[0.1,0.35],trill_rate:[0.15,0.5],duet:[0.02,0.17],variation:[0.4,0.8],rhythm:[0.15,0.45]}},
        {name:'Canary',id:'canary',tip:'A bright, fast rolled whistle.',values:{voice:0,duration:[0.45,1.1],pitch:[0.58,0.76],syllables:[1,3],gap:[0.1,0.22],sweep:[-0.15,0.25],arch:[0.1,0.4],trill:[0.55,0.9],trill_rate:[0.65,1],breath:[0,0.04],rasp:[0,0.03],variation:[0.1,0.4]}},
        {name:'Warbler',id:'warbler',tip:'Two syringeal voices weave a bubbling phrase.',values:{voice:1,duration:[0.65,1.4],pitch:[0.4,0.64],syllables:[3,7],gap:[0.08,0.3],sweep:[-0.4,0.4],arch:[-0.5,0.7],trill:[0.3,0.65],trill_rate:[0.2,0.65],duet:[0.45,0.85],variation:[0.35,0.85],rhythm:[0.2,0.6]}},
        {name:'Parrot',id:'parrot',tip:'A nasal, raspy squawk.',values:{voice:2,duration:[0.3,0.8],pitch:[0.27,0.48],syllables:[1,2],gap:[0.15,0.35],sweep:[-0.6,0.2],arch:[0.3,0.8],trill:[0.15,0.4],duet:[0.15,0.45],rasp:[0.35,0.65],breath:[0.1,0.25]}},
        {name:'Crow',id:'crow',tip:'A hoarse caw with a falling throat.',values:{voice:3,duration:[0.4,1.25],pitch:[0.12,0.3],syllables:[1,3],gap:[0.28,0.48],sweep:[-0.5,-0.15],arch:[0.15,0.45],trill:[0.12,0.32],duet:[0.05,0.2],rasp:[0.55,0.9],breath:[0.08,0.2],variation:[0.05,0.2]}},
        {name:'Owl',id:'owl',tip:'A mellow, hollow hoot.',values:{voice:4,duration:[0.55,1.4],pitch:[0.06,0.23],syllables:[1,3],gap:[0.2,0.4],sweep:[-0.18,0.04],arch:[0.05,0.2],trill:[0.01,0.1],duet:[0,0.06],rasp:[0,0.03],breath:[0.03,0.09],variation:[0.05,0.18]}},
        {name:'Cuckoo',id:'cuckoo',tip:'A paired hollow call with a lower answer.',values:{voice:4,duration:[0.45,0.9],pitch:[0.22,0.35],syllables:2,gap:[0.28,0.4],sweep:[-0.05,0.04],arch:[0.01,0.08],trill:[0,0.035],duet:[0,0.04],rasp:[0,0.02],breath:[0.015,0.045],variation:[0.35,0.5],rhythm:[0,0.08]}},
        {name:'Loon',id:'loon',tip:'A short, rising lake call with a second voice.',values:{voice:1,duration:[0.7,1.7],pitch:[0.25,0.41],syllables:[1,2],gap:[0.08,0.22],sweep:[0.3,0.7],arch:[0.1,0.4],trill:[0.08,0.25],trill_rate:[0.1,0.3],duet:[0.2,0.5],rasp:[0.01,0.08],breath:[0.02,0.08],variation:[0.1,0.3]}}
    ];
    constructor() { super(); this.initialize_presets(); }
    randomize_params() { this.create_random_template(); }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='syllables' && !(checkLocked && this.locked_params[name])) this.params.syllables=Math.round(this.params.syllables);
    }
}

// js/synths/Signlr.js
class Signlr extends PresetSynth {
    name = 'Signlr';
    canvas_bg_logo = 'img/logo_signlr.png';
    tooltip = 'Coded transmissions, derelict beacons and mysterious receivers.';
    static DSP = Signlr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'encoding',display_name:'Encoding',tooltip:'How each symbol changes the carrier.',
            default_value:0,columns:5,values:[['FSK','Bits switch between two frequencies.',0],['Phase','Bits turn the phase of a carrier.',1],
                ['Chirp','Each symbol is a swept sonar pulse.',2],['Radio','A fluttering, filtered receiver.',3],['Ping','A struck, ringing radar marker.',4]]},
        ['Duration','Length of the transmission, in seconds.','duration',1.4,0.15,5],
        ['Carrier','The central transmission frequency.','carrier',0.55,0,1],
        ['Deviation','Frequency spread or depth of phase coding.','deviation',0.35,0,1],
        ['Symbol Rate','From slow beacon characters to rapid data.','symbols',0.4,0,1],
        ['Packets','Number of separately keyed transmission bursts.','packets',3,1,12],
        ['Packet Gap','The portion of each packet left for silence.','gap',0.25,0,0.85],
        ['Drift','A carrier falling or climbing over the transmission.','drift',0,-1,1],
        ['Corruption','Lost symbols and unstable tuning.','corruption',0.08,0,1],
        ['Interference','Receiver static and a nearby unwanted carrier.','interference',0.08,0,1],
        ['Echo','Delayed copies bouncing back from the channel.','echo',0.15,0,1]
    ];
    recipes = [
        {name:'Radar Blip',id:'radar_blip',tip:'One clear return on the scanner.',values:{encoding:4,duration:[.3,.8],carrier:[.45,.7],deviation:[.04,.3],packets:1,gap:[.5,.8],drift:0,interference:0,corruption:0,echo:[.08,.3]}},
        {name:'Target Lock',id:'target_lock',tip:'A bright pair of markers, closing in.',values:{encoding:4,duration:[.5,.9],carrier:[.6,.85],deviation:[.15,.45],packets:2,gap:[.65,.82],drift:[.2,.6],interference:0,corruption:0,echo:[.05,.2]}},
        {name:'Derelict Beacon',id:'derelict_beacon',tip:'A tired navigation beacon still repeating its code.',values:{encoding:0,duration:[1.4,3.2],carrier:[0.22,0.45],deviation:[0.06,0.2],symbols:[0.02,0.15],packets:[2,4],gap:[0.4,0.7],drift:[-0.22,-0.04],corruption:[0.05,0.18],interference:[0.04,0.2],echo:[0.35,0.65]}},
        {name:'Alien Handshake',id:'alien_handshake',tip:'An unfamiliar exchange of shifting coded phrases.',values:{encoding:0,duration:[0.65,1.7],carrier:[0.48,0.75],deviation:[0.5,0.95],symbols:[0.25,0.58],packets:[2,5],gap:[0.1,0.35],drift:[-0.3,0.4],corruption:[0,0.1],interference:[0,0.08],echo:[0.08,0.35]}},
        {name:'Distress Burst',id:'distress_burst',tip:'Urgent short packets through a damaged channel.',values:{encoding:0,duration:[0.6,1.5],carrier:[0.45,0.66],deviation:[0.1,0.28],symbols:[0.05,0.22],packets:[3,6],gap:[0.3,0.56],drift:[-0.08,0.08],corruption:[0,0.08],interference:[0.08,0.25],echo:[0.05,0.25]}},
        {name:'Broken Radio',id:'broken_radio',tip:'Fragments of a wavering receiver amid static.',values:{encoding:3,duration:[1,2.5],carrier:[0.25,0.65],deviation:[0.4,0.95],symbols:[0.25,0.6],packets:[2,5],gap:[0.05,0.3],drift:[-0.8,0.65],corruption:[0.4,0.85],interference:[0.5,0.9],echo:[0,0.15]}},
        {name:'Sonar Map',id:'sonar_map',tip:'Rounded pings and returning echoes from unseen shapes.',values:{encoding:4,duration:[1.4,3.5],carrier:[0.43,0.65],deviation:[0.05,0.25],symbols:[0,0.08],packets:[2,4],gap:[0.28,0.58],drift:[-0.12,0.12],corruption:[0,0.02],interference:[0,0.03],echo:[0.65,1]}},
        {name:'Encrypted Packet',id:'encrypted_packet',tip:'Dense, clipped phase-coded data.',values:{encoding:1,duration:[0.25,0.85],carrier:[0.55,0.82],deviation:[0.65,1],symbols:[0.65,1],packets:[1,3],gap:[0.08,0.3],drift:[-0.05,0.05],corruption:[0,0.1],interference:[0.01,0.08],echo:[0,0.12]}},
        {name:'Lost Satellite',id:'lost_satellite',tip:'A fading orbital signal sweeping out of tune.',values:{encoding:2,duration:[1.5,3.6],carrier:[0.5,0.8],deviation:[0.25,0.7],symbols:[0.12,0.3],packets:[2,5],gap:[0.2,0.5],drift:[-0.95,-0.35],corruption:[0.15,0.45],interference:[0.06,0.25],echo:[0.4,0.85]}},
        {name:'Save Terminal',id:'save_terminal',tip:'A friendly terminal chirping its data into storage.',values:{encoding:0,duration:[0.3,0.85],carrier:[0.45,0.65],deviation:[0.15,0.4],symbols:[0.18,0.38],packets:[2,4],gap:[0.12,0.28],drift:[0.15,0.45],corruption:0,interference:0,echo:[0.03,0.2]}}
    ];
    param_is_disabled(name) { return this.params.encoding===4 && ['symbols','corruption','interference'].includes(name); }
    constructor() { super(); this.initialize_presets(); }
    set_param(name,value,checkLocked=false) {
        super.set_param(name,value,checkLocked);
        if (name==='packets' && !(checkLocked && this.locked_params[name])) {
            this.params.packets=Math.round(this.params.packets);
        }
    }
}

// js/synths/Fractr.js
class Fractr extends PresetSynth {
    name = 'Fractr';
    canvas_bg_logo = 'img/logo_fractr.png';
    tooltip = 'Structural snaps, brittle crunches, cracking ice and falling rubble.';
    static DSP = Fractr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'material', display_name:'Material', tooltip:'The crack, grit and short body of each fragment.',
            default_value:0, columns:4, values:[['Glass','Bright, inharmonic shards.',0],['Ice','Hollow crystalline cracks.',1],
                ['Crystal','Long, almost harmonic ringing.',2],['Stone','Low, dusty rubble.',3],
                ['Armor','Brittle metallic plates.',5],['Bone','A solid, visceral snap and splintering after-cracks.',6],['Biscuit','Porous, dry crunches and crumbling crumbs.',7]]},
        ['Duration','Length of the entire break and its tail, in seconds.','duration',1.8,0.15,6],
        ['Fragments','Number of separately falling pieces.','fragments',32,3,96],
        ['Fragment Size','Larger pieces make deeper, longer contacts; small shards spit and crackle.','fragmentSize',0.4,0,1],
        ['Spread','Time between the first and last fractures.','spread',0.6,0,1],
        ['Decay','Length of the grit after each crack; Crystal also sustains its ringing.','decay',0.4,0,1],
        ['Gravity','Stronger gravity speeds the cascade and shortens bounce flights.','gravity',0.5,0,1],
        ['Bounce','Number and strength of each fragment’s returning contacts.','bounce',0.4,0,1],
        ['Stress','Straining, creaking microfractures before the material lets go.','stress',0.4,0,1],
        ['Shards','Loose fragment and contact level, independent of the main structural snap.','shards',0.35,0,1],
        ['Fracture','Strength of the initial structural split and its branching cracks.','fracture',0.75,0,1]
    ];
    recipes = [
        {name:'Glass Cascade',id:'glass_cascade',tip:'A fresh shower of bright glass shards.',values:{stress:[0.05,0.25],fracture:[0.65,1],shards:[0.5,0.9],material:0,duration:[1.1,2.6],fragments:[30,72],fragmentSize:[0.18,0.46],spread:[0.45,0.85],decay:[0.2,0.5],gravity:[0.35,0.7],bounce:[0.45,0.8]}},
        {name:'Ice Wall',id:'ice_wall',tip:'A wall splitting into cold, hollow chunks.',values:{stress:[0.65,1],fracture:[0.7,1],material:1,duration:[1.6,3.1],fragments:[20,50],fragmentSize:[0.5,0.85],spread:[0.55,0.95],decay:[0.3,0.6],gravity:[0.2,0.6],bounce:[0.2,0.5]}},
        {name:'Crystal Break',id:'crystal_break',tip:'A magical crystal scattering ringing fragments.',values:{stress:[0.1,0.3],fracture:[0.45,0.85],shards:[0.65,1],material:2,duration:[1.2,3.2],fragments:[8,28],fragmentSize:[0.1,0.45],spread:[0.12,0.4],decay:[0.65,1],gravity:[0.1,0.4],bounce:[0.25,0.6]}},
        {name:'Stone Collapse',id:'stone_collapse',tip:'Heavy rubble falling through a collapsing structure.',values:{stress:[0.5,0.9],fracture:[0.7,1],shards:[0.6,1],material:3,duration:[2.2,4.6],fragments:[40,96],fragmentSize:[0.55,1],spread:[0.7,1],decay:[0.25,0.7],gravity:[0.5,0.9],bounce:[0.35,0.75]}},
        {name:'Brittle Armor',id:'brittle_armor',tip:'A sharp armor break followed by scattered plates.',values:{stress:[0.3,0.65],fracture:[0.85,1],material:5,duration:[0.55,1.5],fragments:[7,24],fragmentSize:[0.35,0.75],spread:[0.08,0.35],decay:[0.18,0.48],gravity:[0.55,1],bounce:[0.5,0.9]}},
        {name:'Bone Snap',id:'bone_scatter',tip:'A forceful close snap, splinters and a brief fleshy body.',values:{stress:[0.1,0.5],fracture:[0.85,1],shards:[0.04,0.16],material:6,duration:[0.22,0.48],fragments:[3,8],fragmentSize:[0.55,0.9],spread:[0.01,0.09],decay:[0.03,0.14],gravity:[0.8,1],bounce:[0,0.12]}},
        {name:'Shatter Freeze',id:'shatter_freeze',tip:'A suspended fracture that slowly sheds chiming shards.',values:{stress:[0.7,1],fracture:[0.35,0.65],material:[0,2],duration:[3,5.5],fragments:[18,46],fragmentSize:[0.15,0.5],spread:[0.8,1],decay:[0.65,1],gravity:[0,0.1],bounce:[0.08,0.3]}},
        {name:'Glass Snap',id:'glass_snap',tip:'A thin pane cleaves with a sharp snap and a few tiny chips.',values:{material:0,duration:[0.18,0.4],stress:[0.05,0.25],fracture:[0.8,1],shards:[0.03,0.12],fragments:[3,9],fragmentSize:[0.1,0.35],spread:[0.01,0.06],decay:[0.02,0.12],gravity:[0.7,1],bounce:[0,0.15]}},
        {name:'Ice Crack',id:'ice_crack',tip:'A thick sheet of ice splits in branching, hollow cracks.',values:{material:1,duration:[0.3,0.65],stress:[0.3,0.7],fracture:[0.8,1],shards:[0.04,0.18],fragments:[3,10],fragmentSize:[0.55,0.9],spread:[0.03,0.15],decay:[0.08,0.2],gravity:[0.6,0.9],bounce:[0,0.1]}},
        {name:'Biscuit Crunch',id:'biscuit_crunch',tip:'A dry bite crushes a brittle crust into irregular crumbs.',values:{material:7,duration:[0.22,0.5],stress:[0.15,0.45],fracture:[0.8,1],shards:[0.03,0.12],fragments:[8,24],fragmentSize:[0.25,0.6],spread:[0.03,0.13],decay:[0.02,0.12],gravity:[0.7,1],bounce:[0,0.12]}}
    ];
    randomize_params() {
        this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id);
    }
    // Old saves and external callers can retain the original ID without a Pixel button.
    generate_pixel_disintegrate() {
        this.generate_recipe('crystal_break');
        this.set_param('material',4,true);
    }
    generate_recipe(id) {
        if(id==='pixel_disintegrate') return this.generate_pixel_disintegrate();
        super.generate_recipe(id);
    }
    apply_params(params,checkLocked=false) {
        if(!params||typeof params!=='object')return;
        // Complete older snapshots need defaults for controls they never stored.
        // A partial edit must leave unrelated current controls untouched.
        const oldKeys=['masterVolume','seed','material','duration','fragments','fragmentSize','spread','decay','gravity','bounce'];
        if(oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['stress','fracture','shards']) if(!Object.prototype.hasOwnProperty.call(params,key)) {
                this.set_param(key,this.param_default(key),checkLocked);
            }
        }
        super.apply_params(params,checkLocked);
    }
    constructor() { super(); this.initialize_presets(); }
    set_param(name, value, checkLocked = false) {
        if(name==='material' && value===4) {
            if(!(checkLocked && this.locked_params[name])) { this.params.material=4; this.sound_params=null; }
            return;
        }
        super.set_param(name, value, checkLocked);
        if (name === 'fragments' && !(checkLocked && this.locked_params[name])) {
            this.params.fragments = Math.round(this.params.fragments);
        }
    }
}

// js/synths/Riftr.js
class Riftr extends PresetSynth {
    name = 'Riftr';
    canvas_bg_logo = 'img/logo_riftr.png';
    tooltip = 'Warped spaces, force fields and reversals through a moving resonant field.';
    static DSP = Riftr_DSP;
    param_info = [
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT', name:'excitation', display_name:'Excitation', tooltip:'What enters the resonant field.',
            default_value:0, columns:5, values:[['Pulse','A short tonal impulse.',0],['Arc','A swelling electrical arc.',1],
                ['Drone','A sustained, pulsing field.',2],['Tear','A noisy rupture with a low body.',3],['Quanta','Separated packets of phase-shifted tone.',4]]},
        ['Duration','Length of the complete effect, in seconds.','duration',1.8,0.15,6],
        ['Pitch','Pitch of the signal entering the field.','pitch',0.45,0,1],
        ['Bend','Pitch travel from falling to rising.','bend',-0.2,-1,1],
        ['Space','Propagation distance inside the field; larger spaces echo more slowly.','space',0.5,0,1],
        ['Feedback','How much energy returns through the field.','feedback',0.65,0,1],
        ['Dispersion','Allpass delays scatter the field into a smeared, metallic tail.','dispersion',0.55,0,1],
        ['Motion','Moving delay taps bend the field’s phase and pitch.','motion',0.3,0,1],
        ['Field Mix','Blend between the source and its resonant field.','field',0.7,0,1],
        ['Reverse','Blend the finished field with time running backwards.','reverse',0,0,1]
    ];
    recipes = [
        {name:'Gravity Well',id:'gravity_well',tip:'A descending tone trapped in a tightening field.',values:{excitation:1,duration:[1.5,3],pitch:[0.35,0.6],bend:[-1,-0.55],space:[0.45,0.8],feedback:[0.65,0.9],dispersion:[0.4,0.8],motion:[0.15,0.5],field:[0.6,0.9],reverse:[0,0.12]}},
        {name:'Time Rewind',id:'time_rewind',tip:'A dispersed impact pulling itself back together.',values:{excitation:0,duration:[1,2.6],pitch:[0.45,0.8],bend:[-0.65,0.3],space:[0.35,0.75],feedback:[0.72,0.95],dispersion:[0.6,1],motion:[0.1,0.5],field:[0.7,1],reverse:[0.93,1]}},
        {name:'Phase Dash',id:'phase_dash',tip:'A short upward arc slipping through a small space.',values:{excitation:1,duration:[0.18,0.5],pitch:[0.25,0.65],bend:[0.35,0.95],space:[0.03,0.25],feedback:[0.15,0.5],dispersion:[0.15,0.5],motion:[0.55,1],field:[0.35,0.7],reverse:[0,0.15]}},
        {name:'Force Field',id:'force_field',tip:'An energized barrier humming through its resonant geometry.',values:{excitation:2,duration:[1.5,3.8],pitch:[0.18,0.5],bend:[-0.12,0.12],space:[0.04,0.35],feedback:[0.72,0.98],dispersion:[0.15,0.55],motion:[0.2,0.55],field:[0.55,0.85],reverse:[0,0.2]}},
        {name:'Portal Tear',id:'portal_tear',tip:'A ragged opening scattering sound through a large space.',values:{excitation:3,duration:[1,2.8],pitch:[0.25,0.55],bend:[0.3,0.9],space:[0.5,0.95],feedback:[0.55,0.9],dispersion:[0.7,1],motion:[0.5,1],field:[0.5,0.9],reverse:[0.15,0.4]}},
        {name:'Teleport Arrive',id:'teleport_arrive',tip:'A reversed field gathering into a bright arrival.',values:{excitation:0,duration:[0.45,1.2],pitch:[0.6,0.95],bend:[-0.7,-0.1],space:[0.15,0.5],feedback:[0.55,0.85],dispersion:[0.3,0.8],motion:[0.1,0.6],field:[0.45,0.8],reverse:[0.78,1]}},
        {name:'Black Hole',id:'black_hole',tip:'A low drone falling into a deep resonant cavity.',values:{excitation:2,duration:[2.5,5],pitch:[0.05,0.25],bend:[-1,-0.45],space:[0.65,1],feedback:[0.85,1],dispersion:[0.65,1],motion:[0.05,0.3],field:[0.55,0.9],reverse:[0,0.18]}},
        {name:'Reality Glitch',id:'reality_glitch',tip:'Phase packets echoing forwards and backwards.',values:{excitation:4,duration:[0.65,1.9],pitch:[0.45,0.95],bend:[-0.8,0.9],space:[0.08,0.55],feedback:[0.45,0.85],dispersion:[0.25,0.9],motion:[0.7,1],field:[0.4,0.8],reverse:[0.25,0.75]}}
    ];
    constructor() { super(); this.initialize_presets(); }
}

// js/synths/Swarmr.js
class Swarmr extends PresetSynth {
    name='Swarmr';
    canvas_bg_logo = 'img/logo_swarmr.png';
    tooltip='Flocks, clouds and coordinated little machines.';
    static DSP=Swarmr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'kind',display_name:'Agents',tooltip:'The individual sound inside the swarm.',default_value:0,columns:3,header:true,
            values:[['Wings','Independent wing strokes and rushing air.',0],['Chirps','Brief calls.',1],['Rotors','Small motors with rough blade wakes.',2],
                ['Ticks','Paired skittering feet and joint clicks.',3],['Wisps','Soft hovering tones.',4],['Jets','Tiny rushing exhausts.',5]]},
        ['Duration','Seconds.','duration',1.8,0.25,5],
        ['Population','Number of independent emitters.','count',14,3,32],
        ['Speed','Wingbeats, chirps and repeated activity.','speed',0.5,0,1],
        ['Cohesion','Synchronize the individual calls and movement.','cohesion',0.3,0,1],
        ['Agitation','Unsteady flight and pitch.','agitation',0.25,0,1],
        ['Size','Larger agents have lower voices.','size',0.45,0,1],
        ['Flyby','Approach and recede, changing pitch and level.','movement',0.5,0,1],
        ['Scatter','Spread the agents’ arrivals over time.','scatter',0.2,0,1]
    ];
    recipes=[
        {name:'Nanobots',id:'nanobots',tip:'A cloud of busy microscopic machines.',values:{kind:3,duration:[0.6,1.6],count:[16,32],speed:[0.65,1],cohesion:[0.1,0.4],agitation:[0.5,1],size:[0,0.25],movement:[0.1,0.5],scatter:[0.1,0.5]}},
        {name:'Cave Bats',id:'cave_bats',tip:'A startled flock leaving its roost.',values:{kind:0,duration:[1.2,2.6],count:[8,19],speed:[0.3,0.65],cohesion:[0.05,0.3],agitation:[0.55,0.95],size:[0.5,0.8],movement:[0.6,1],scatter:[0.25,0.8]}},
        {name:'Fireflies',id:'fireflies',tip:'Little overlapping points of sound.',values:{kind:1,duration:[1.3,3],count:[4,12],speed:[0.05,0.28],cohesion:[0.05,0.3],agitation:[0,0.2],size:[0.05,0.3],movement:[0.05,0.3],scatter:[0.1,0.65]}},
        {name:'Scarabs',id:'scarabs',tip:'A shifting carpet of hard little feet.',values:{kind:3,duration:[1,2.5],count:[15,32],speed:[0.15,0.55],cohesion:[0,0.2],agitation:[0.2,0.6],size:[0.65,1],movement:[0.05,0.4],scatter:[0.15,0.6]}},
        {name:'Drone Patrol',id:'drone_patrol',tip:'A formation of small flying machines.',values:{kind:2,duration:[1.6,3.8],count:[3,8],speed:[0.15,0.55],cohesion:[0.55,0.95],agitation:[0.02,0.25],size:[0.5,0.95],movement:[0.7,1],scatter:[0,0.3]}},
        {name:'Fairy Flock',id:'fairy_flock',tip:'A small migrating cloud of shimmering voices.',values:{kind:4,duration:[1.4,3.3],count:[6,17],speed:[0.1,0.35],cohesion:[0.4,0.85],agitation:[0.1,0.4],size:[0.1,0.5],movement:[0.15,0.65],scatter:[0.1,0.6]}},
        {name:'Locusts',id:'locusts',tip:'A dense, restless wing cloud.',values:{kind:0,duration:[1.5,3.3],count:[22,32],speed:[0.65,1],cohesion:[0,0.22],agitation:[0.65,1],size:[0.05,0.3],movement:[0.1,0.55],scatter:[0,0.3]}},
        {name:'Seeking Missiles',id:'seeking_missiles',tip:'Several tiny rockets rush past.',values:{kind:5,duration:[0.7,1.8],count:[3,7],speed:[0.6,1],cohesion:[0.2,0.65],agitation:[0.4,0.9],size:[0.2,0.7],movement:[0.8,1],scatter:[0.2,0.9]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        if(name==='count'&&Number.isFinite(value))value=Math.round(value);
        super.set_param(name,value,checkLocked);
    }
}

// js/synths/Rustlr.js
class Rustlr extends PresetSynth {
    name='Rustlr';
    canvas_bg_logo = 'img/logo_rustlr.png';
    tooltip='Paper, fabric and small inventory-handling gestures.';
    static DSP=Rustlr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'Material',tooltip:'The surface being handled.',default_value:0,columns:3,
            values:[['Paper','Dry fibers and crisp creases.',0],['Cloth','Soft fabric friction.',1],['Leather','A low, leathery rub.',2],
                ['Plastic','Light, crackly film.',3],['Foil','Bright metallic wrinkles.',4],['Zip','Closely spaced zipper teeth.',5]]},
        {type:'BUTTONSELECT',name:'gesture',display_name:'Gesture',tooltip:'How the movement develops.',default_value:1,columns:4,
            values:[['Flick','A quick movement that falls away.',0],['Turn','A broad bending movement.',1],
                ['Slide','Sustained contact along a surface.',2],['Crumple','Repeated pinches and releases.',3]]},
        ['Duration','Complete movement length in seconds.','duration',0.65,0.08,3],
        ['Grain','From tiny surface grains to broad rubbing contacts.','grain',0.45,0,1],
        ['Density','The number and overlap of surface microcontacts.','density',0.5,0,1],
        ['Motion','Emphasize the start or the arrival of the movement.','motion',0,-1,1],
        ['Pressure','Contact force, elastic loading and friction releases.','pressure',0.5,0,1],
        ['Folds','Number of distinct bends or creases.','folds',3,1,12],
        ['Brightness','Detail in the upper friction frequencies.','brightness',0.5,0,1]
    ];
    recipes=[
        {name:'Card Flick',id:'card_flick',tip:'A small card or inventory tile flicks into place.',values:{material:0,gesture:0,duration:[0.12,0.24],grain:[0.12,0.36],density:[0.4,0.7],motion:[-0.4,0.2],pressure:[0.35,0.65],folds:[1,2],brightness:[0.52,0.85]}},
        {name:'Page Turn',id:'page_turn',tip:'A paper page bends and settles.',values:{material:0,gesture:1,duration:[0.45,0.85],grain:[0.35,0.68],density:[0.5,0.83],motion:[-0.25,0.45],pressure:[0.3,0.6],folds:[2,4],brightness:[0.38,0.7]}},
        {name:'Bag Open',id:'bag_open',tip:'A soft pouch pulls open.',values:{material:[1,2],gesture:1,duration:[0.38,0.8],grain:[0.55,0.88],density:[0.55,0.9],motion:[0.1,0.7],pressure:[0.45,0.8],folds:[2,5],brightness:[0.22,0.55]}},
        {name:'Equip Gear',id:'equip_gear',tip:'Leather and fabric settle around an equipped item.',values:{material:2,gesture:[1,3],duration:[0.3,0.65],grain:[0.35,0.68],density:[0.48,0.8],motion:[-0.25,0.35],pressure:[0.62,0.9],folds:[3,6],brightness:[0.4,0.7]}},
        {name:'Item Slide',id:'item_slide',tip:'An item slides across a surface.',values:{material:[0,2,3],gesture:2,duration:[0.2,0.46],grain:[0.18,0.45],density:[0.65,0.93],motion:[-0.65,0.3],pressure:[0.35,0.64],folds:[1,3],brightness:[0.35,0.7]}},
        {name:'Cloth Fold',id:'cloth_fold',tip:'A soft inventory bundle folds into place.',values:{material:1,gesture:1,duration:[0.32,0.72],grain:[0.65,0.95],density:[0.65,1],motion:[-0.2,0.55],pressure:[0.62,0.95],folds:[2,4],brightness:[0.25,0.6]}},
        {name:'Wrapper',id:'wrapper',tip:'A thin wrapper wrinkles and unfolds.',values:{material:[3,4],gesture:3,duration:[0.38,0.85],grain:[0.18,0.48],density:[0.4,0.75],motion:[-0.25,0.4],pressure:[0.42,0.72],folds:[4,9],brightness:[0.6,0.93]}},
        {name:'Zip Pouch',id:'zip_pouch',tip:'A short zipper pulls through its teeth.',values:{material:5,gesture:2,duration:[0.25,0.62],grain:[0.06,0.27],density:[0.24,0.58],motion:[-0.45,0.65],pressure:[0.48,0.8],folds:[1,3],brightness:[0.45,0.8]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='folds' && !(checkLocked && this.locked_params[name])) this.params.folds=Math.round(this.params.folds);
    }
}

// js/synths/Boomr.js
class Boomr extends PresetSynth {
    name='Boomr';
    canvas_bg_logo = 'img/logo_boomr.png';
    tooltip='Pressure waves, fireballs and falling fragments.';
    static DSP=Boomr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        ['Duration','Seconds.','duration',1.5,0.12,5],
        ['Size','Larger blasts have a deeper pressure body and slower, darker fireballs.','size',0.5,0,1],
        ['Pressure','The low shock front of the explosion.','pressure',0.7,0,1],
        ['Blast','The initial turbulent fireball.','blast',0.65,0,1],
        ['Debris','Sharp grit and dull rubble contacts after the blast.','debris',0.35,0,1],
        ['Gas','Sustained escaping gas, rising after the initial rupture.','gas',0.25,0,1],
        ['Aftershock','Delayed ground pulses and secondary pressure fronts.','aftershock',0.25,0,1],
        ['Rubble Size','Fine shrapnel at the left; heavy, low chunks at the right.','rubbleSize',0.5,0,1],
        ['Scatter','Spread the fragments through the tail.','spread',0.5,0,1],
        ['Aftermath','Length and weight of the rolling decay.','tail',0.45,0,1],
        ['Muffle','Lose sharp detail behind walls or underwater.','muffle',0.15,0,1],
        {type:'BUTTONSELECT',name:'mechanism',display_name:'Explosion',tooltip:'How the stored energy is released.',default_value:0,columns:3,
            values:[['Detonation','A sudden pressure front with turbulent air.',0],['Fuel','A swelling fire bloom and hollow shell.',1],['Underwater','Deep pressure and rebounding cavitation bubbles.',2],['Impact','Ground transmission and an ejecta cone.',3],['Collapse','Successive structural failures.',4],['Pop','A tiny, dry rupture.',5],['Gas Rupture','A pressure vessel opens into a turbulent jet.',6],['Implosion','Inward suction gives way to a dense collapse.',7]]},
        ['Space','Diffuse pressure reflections and a spacious rolling tail.','space',0.25,0,1]
    ];
    recipes=[
        {name:'Grenade',id:'grenade',tip:'A sharp pressure thump and loose shrapnel.',values:{gas:[0.03,0.15],aftershock:[0.05,0.22],rubbleSize:[0.05,0.35],mechanism:0,space:[0.08,0.35],duration:[0.65,1.5],size:[0.25,0.55],pressure:[0.65,1],blast:[0.45,0.8],debris:[0.55,0.95],spread:[0.3,0.7],tail:[0.2,0.5],muffle:[0.03,0.25]}},
        {name:'Barrel',id:'barrel',tip:'A hollow fuel drum erupting.',values:{gas:[0.65,1],aftershock:[0.1,0.3],rubbleSize:[0.25,0.55],mechanism:1,space:[0.25,0.55],duration:[1,2],size:[0.4,0.7],pressure:[0.5,0.85],blast:[0.7,1],debris:[0.65,1],spread:[0.15,0.55],tail:[0.45,0.8],muffle:[0.1,0.35]}},
        {name:'Rocket',id:'rocket',tip:'A hard detonation with a tearing fireball.',values:{gas:[0.25,0.6],aftershock:[0.25,0.6],rubbleSize:[0.05,0.3],mechanism:0,space:[0.2,0.5],duration:[0.7,1.6],size:[0.3,0.65],pressure:[0.8,1],blast:[0.8,1],debris:[0.2,0.5],spread:[0.05,0.3],tail:[0.3,0.65],muffle:[0,0.18]}},
        {name:'Depth Charge',id:'depth_charge',tip:'An immense muffled underwater pressure wave.',values:{gas:[0,0.04],aftershock:[0.7,1],rubbleSize:[0.7,1],mechanism:2,space:[0.4,0.85],duration:[1.8,3.6],size:[0.8,1],pressure:[0.85,1],blast:[0.4,0.8],debris:[0,0.15],spread:[0.4,0.8],tail:[0.65,1],muffle:[0.75,1]}},
        {name:'Fireball',id:'fireball',tip:'A bloom of flame with a rolling hot tail.',values:{gas:[0.7,1],aftershock:[0.02,0.15],rubbleSize:[0.1,0.3],mechanism:1,space:[0.35,0.75],duration:[1.3,2.8],size:[0.45,0.8],pressure:[0.3,0.6],blast:[0.85,1],debris:[0.02,0.22],spread:[0.2,0.55],tail:[0.7,1],muffle:[0.2,0.5]}},
        {name:'Meteor',id:'meteor',tip:'A massive impact and scattered incandescent rubble.',values:{gas:[0.1,0.4],aftershock:[0.8,1],rubbleSize:[0.8,1],mechanism:3,space:[0.6,1],duration:[2.2,4.5],size:[0.85,1],pressure:[0.85,1],blast:[0.65,0.95],debris:[0.75,1],spread:[0.65,1],tail:[0.7,1],muffle:[0.3,0.6]}},
        {name:'Demolition',id:'demolition',tip:'A heavy charge followed by falling structure.',values:{gas:[0.08,0.22],aftershock:[0.5,0.9],rubbleSize:[0.6,1],mechanism:4,space:[0.5,0.9],duration:[1.6,3.8],size:[0.65,0.95],pressure:[0.65,0.9],blast:[0.4,0.7],debris:[0.85,1],spread:[0.7,1],tail:[0.45,0.85],muffle:[0.15,0.4]}},
        {name:'Tiny Pop',id:'tiny_pop',tip:'A miniature comic detonation.',values:{gas:0,aftershock:0,rubbleSize:[0,0.2],mechanism:5,space:[0,0.08],duration:[0.12,0.35],size:[0,0.2],pressure:[0.55,0.85],blast:[0.1,0.4],debris:[0,0.12],spread:[0,0.25],tail:[0,0.18],muffle:[0,0.12]}},
        {name:'Gas Tank',id:'gas_tank',tip:'A vessel ruptures, then vents a long rough jet.',values:{mechanism:6,duration:[1.3,3.4],size:[0.25,0.7],pressure:[0.3,0.65],blast:[0.2,0.5],gas:[0.8,1],aftershock:[0,0.08],debris:[0.02,0.2],rubbleSize:[0.15,0.4],spread:[0.3,0.6],tail:[0.4,0.8],muffle:[0,0.2],space:[0.05,0.25]}},
        {name:'Implosion',id:'implosion',tip:'A short inward rush and deep, crumpling structural failure.',values:{mechanism:7,duration:[0.8,2.1],size:[0.6,1],pressure:[0.8,1],blast:[0.2,0.45],gas:[0.03,0.12],aftershock:[0.15,0.4],debris:[0.6,1],rubbleSize:[0.7,1],spread:[0.15,0.45],tail:[0.15,0.4],muffle:[0.25,0.5],space:[0.1,0.35]}},
        {name:'Distant Charge',id:'distant_charge',tip:'A deep distant thud with separated ground shocks and settling rubble.',values:{mechanism:0,duration:[2,4.5],size:[0.85,1],pressure:[0.65,1],blast:[0.03,0.15],gas:[0,0.1],aftershock:[0.7,1],debris:[0.1,0.35],rubbleSize:[0.8,1],spread:[0.6,1],tail:[0.7,1],muffle:[0.65,0.9],space:[0.7,1]}}
    ];
    randomize_params() {
        this.generate_recipe(this.recipes[Math.floor(Math.random()*this.recipes.length)].id);
    }
    apply_params(params,checkLocked=false) {
        if(!params||typeof params!=='object')return;
        // Complete older snapshots need defaults for controls they never stored.
        // A partial edit must leave unrelated current controls untouched.
        const oldKeys=['masterVolume','seed','duration','size','pressure','blast','debris','spread','tail','muffle'];
        if(oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['mechanism','space','gas','aftershock','rubbleSize']) if(!Object.prototype.hasOwnProperty.call(params,key)) {
                this.set_param(key,this.param_default(key),checkLocked);
            }
        }
        super.apply_params(params,checkLocked);
    }
    constructor(){super();this.initialize_presets();}
}

// js/synths/Zappr.js
class Zappr extends PresetSynth {
    name='Zappr';
    canvas_bg_logo = 'img/logo_zappr.png';
    tooltip='Branching arcs, charged fields and electrical failures.';
    static DSP=Zappr_DSP;
    param_info=[
        ...PresetSynth.common_params,
        ['Duration','Seconds.','duration',1.2,0.12,5],
        ['Voltage','Raises the frequency and agitation of the current.','voltage',0.55,0,1],
        ['Arcs','Number of primary discharges.','arcs',7,1,24],
        ['Branching','Smaller discharges split from each main arc.','branching',0.4,0,1],
        ['Crackle','Irregular tiny contacts between the main arcs.','crackle',0.45,0,1],
        ['Hum','Low electrical field beneath the discharge.','hum',0.2,0,1],
        ['Sparks','Move from ringing arcs to noisy sparks.','spark',0.65,0,1],
        ['Spread','Spread the discharges over the duration.','spread',0.7,0,1],
        ['Decay','Length of each electrical discharge.','decay',0.4,0,1]
    ];
    recipes=[
        {name:'Static Spark',id:'static_spark',tip:'A little sharp discharge from a fingertip.',values:{duration:[0.12,0.3],voltage:[0.55,0.9],arcs:[1,3],branching:[0,0.15],crackle:[0,0.2],hum:[0,0.02],spark:[0.8,1],spread:[0,0.2],decay:[0,0.12]}},
        {name:'Tesla Coil',id:'tesla_coil',tip:'A buzzing field throws branching arcs.',values:{duration:[1.3,2.8],voltage:[0.7,1],arcs:[14,24],branching:[0.65,1],crackle:[0.45,0.8],hum:[0.45,0.8],spark:[0.25,0.6],spread:[0.7,1],decay:[0.25,0.6]}},
        {name:'Power Short',id:'power_short',tip:'A failing connection spits and buzzes.',values:{duration:[0.5,1.5],voltage:[0.25,0.6],arcs:[5,12],branching:[0.2,0.6],crackle:[0.8,1],hum:[0.3,0.65],spark:[0.65,1],spread:[0.35,0.8],decay:[0.05,0.3]}},
        {name:'Lightning Arc',id:'lightning_arc',tip:'A single great fork of electrical energy.',values:{duration:[0.5,1.3],voltage:[0.8,1],arcs:[1,3],branching:[0.85,1],crackle:[0.05,0.25],hum:[0,0.12],spark:[0.45,0.8],spread:[0.02,0.18],decay:[0.65,1]}},
        {name:'Stun Baton',id:'stun_baton',tip:'A close, rapidly sparking electric weapon.',values:{duration:[0.4,1.1],voltage:[0.5,0.8],arcs:[9,20],branching:[0.25,0.6],crackle:[0.7,1],hum:[0.15,0.4],spark:[0.55,0.9],spread:[0.75,1],decay:[0.05,0.25]}},
        {name:'Reactor',id:'reactor',tip:'A heavy field with unstable internal discharges.',values:{duration:[2,4.5],voltage:[0.1,0.35],arcs:[8,18],branching:[0.3,0.75],crackle:[0.3,0.7],hum:[0.8,1],spark:[0.1,0.4],spread:[0.75,1],decay:[0.55,0.95]}},
        {name:'Magic Spark',id:'magic_spark',tip:'A bright ringing cluster of impossible energy.',values:{duration:[0.4,1.2],voltage:[0.6,0.95],arcs:[3,8],branching:[0.6,1],crackle:[0,0.15],hum:[0,0.08],spark:[0,0.2],spread:[0.4,0.8],decay:[0.45,0.8]}},
        {name:'Fuse Blow',id:'fuse_blow',tip:'A brief, harsh electrical failure.',values:{duration:[0.15,0.5],voltage:[0.4,0.75],arcs:[2,5],branching:[0.4,0.8],crackle:[0.4,0.75],hum:[0.1,0.4],spark:[0.8,1],spread:[0,0.18],decay:[0.1,0.35]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){
        super.set_param(name,value,checkLocked);
        if(name==='arcs'&&!(checkLocked&&this.locked_params[name]))this.params.arcs=Math.round(this.params.arcs);
    }
}

// js/synths/Whooshr.js
class Whooshr extends PresetSynth {
    name='Whooshr';
    canvas_bg_logo = 'img/logo_whooshr.png';
    tooltip='Swings, flybys and rushing air.';
    static DSP=Whooshr_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Seconds.','duration',0.6,0.1,5],
        ['Size','Large objects push deeper air.','size',0.4,0,1],
        ['Air','Filtered rushing turbulence.','air',0.8,0,1],
        ['Whistle','The pitched edge of a fast object.','whistle',0.25,0,1],
        ['Flyby','Pitch falls as the object passes.','movement',0.7,0,1],
        ['Focus','Concentrate the rush around its closest approach.','focus',0.6,0,1],
        ['Flutter','Uneven folds, feathers and trailing edges.','flutter',0.1,0,1]
    ];
    recipes=[
        {name:'Sword Swing',id:'sword_swing',values:{duration:[0.18,0.42],size:[0.25,0.5],air:[0.6,0.9],whistle:[0.25,0.55],movement:[0.65,1],focus:[0.5,0.85],flutter:[0,0.1]}},
        {name:'Dodge',id:'dodge',values:{duration:[0.25,0.55],size:[0.5,0.8],air:[0.75,1],whistle:[0,0.1],movement:[0.2,0.6],focus:[0.3,0.65],flutter:[0.1,0.3]}},
        {name:'Arrow Pass',id:'arrow_pass',values:{duration:[0.16,0.4],size:[0.05,0.3],air:[0.3,0.65],whistle:[0.5,0.9],movement:[0.8,1],focus:[0.65,1],flutter:[0,0.1]}},
        {name:'Heavy Swing',id:'heavy_swing',values:{duration:[0.4,0.9],size:[0.8,1],air:[0.8,1],whistle:[0.05,0.2],movement:[0.5,0.85],focus:[0.3,0.6],flutter:[0.05,0.25]}},
        {name:'Fast Projectile',id:'fast_projectile',values:{duration:[0.1,0.25],size:[0,0.2],air:[0.65,1],whistle:[0.3,0.7],movement:[0.9,1],focus:[0.7,1],flutter:[0,0.08]}},
        {name:'Wingbeat',id:'wingbeat',values:{duration:[0.35,0.85],size:[0.55,0.9],air:[0.6,0.9],whistle:[0,0.08],movement:[0.1,0.4],focus:[0.15,0.45],flutter:[0.65,1]}},
        {name:'Cloth Swipe',id:'cloth_swipe',values:{duration:[0.25,0.7],size:[0.4,0.75],air:[0.65,1],whistle:[0,0.04],movement:[0.1,0.4],focus:[0.25,0.55],flutter:[0.4,0.8]}},
        {name:'Air Dash',id:'air_dash',values:{duration:[0.35,0.85],size:[0.3,0.65],air:[0.75,1],whistle:[0.15,0.4],movement:[0.65,1],focus:[0.1,0.35],flutter:[0.05,0.2]}}
    ];
    constructor(){super();this.initialize_presets();}
}

// js/synths/Bouncr.js
class Bouncr extends PresetSynth {
    // Keep the saved engine identity while showing its friendly name.
    name='Bouncr';
    canvas_bg_logo = 'img/logo_bouncr.png';
    display_name='Bonks';
    hide_params=['masterVolume','count','bounce','gravity','spin'];
    tooltip='An object of one material striking a surface of another.';
    static DSP=Bouncr_DSP;
    param_info=[PresetSynth.common_params[0],
        {type:'BUTTONSELECT',name:'material',display_name:'Object',tooltip:'The material of the object arriving at the surface.',default_value:0,columns:3,header:true,values:[['Rubber','Soft elastic body.',0],['Wood','Dry, hollow knock.',1],['Metal','Dense ringing body.',2],['Glass','Bright, brittle resonances.',3],['Stone','Heavy, granular body.',4]]},
        {type:'BUTTONSELECT',name:'surface',display_name:'Surface',tooltip:'The receiving surface has its own resonance and absorbs the object differently.',default_value:0,columns:3,header:true,values:[['Concrete','Dense, short clack.',0],['Wood','Hollow board resonance.',1],['Metal','Long ringing panel.',2],['Glass','Thin bright pane.',3],['Earth','Loose, grainy absorption.',4],['Fabric','Soft, muffled landing.',5]]},
        ['Force','Strike velocity changes contact compression and transferred energy.','force',0.65,0,1],
        ['Duration','Length of the rendered sound in seconds.','duration',2,0.2,5],
        ['Mass / Size','Larger, heavier objects excite lower body and surface modes.','size',0.5,0,1],
        ['Hardness','Contact stiffness: a soft thud through to a sharp strike.','hardness',0.6,0,1],
        ['Tail','Damping and resonant decay after the impact.','tail',0.4,0,1],
        PresetSynth.common_params[1],
        ['Contacts','One impact, or optional diminishing rebounds.','count',1,1,20],
        ['Elasticity','Body resilience and energy retained by optional rebounds.','bounce',0.65,0,1],
        ['Gravity','Stronger gravity shortens the gap between optional rebounds.','gravity',0.5,0,1],
        ['Spin','An angled collision adds rubbing and a settling rattle.','spin',0,0,1]
    ];
    recipes=[
        {name:'Rubber on Wood',id:'rubber_ball',values:{material:0,surface:1,duration:[0.5,1.2],count:1,size:[0.35,0.75],hardness:[0.15,0.45],bounce:[0.5,0.9],force:[0.35,0.8],tail:[0.2,0.55]}},
        {name:'Steel on Concrete',id:'metal_ball',values:{material:2,surface:0,duration:[0.5,1.4],count:1,size:[0.4,0.8],hardness:[0.7,1],force:[0.5,1],tail:[0.2,0.6],spin:[0,0.25]}},
        {name:'Wood on Metal',id:'wooden_dice',values:{material:1,surface:2,duration:[0.8,1.8],count:1,size:[0.2,0.6],hardness:[0.45,0.85],force:[0.4,0.85],tail:[0.4,0.85],spin:[0,0.25]}},
        {name:'Heavy Soft Landing',id:'basketball',values:{material:[0,4],surface:5,duration:[0.4,1.1],count:1,size:[0.7,1],hardness:[0.15,0.45],force:[0.65,1],tail:[0.1,0.45]}},
        {name:'Glass on Stone',id:'marble',values:{material:3,surface:0,duration:[0.5,1.3],count:1,size:[0.05,0.35],hardness:[0.7,1],force:[0.3,0.65],tail:[0.3,0.7]}},
        {name:'Coin on Glass',id:'coin_spin',values:{material:2,surface:3,duration:[0.7,1.8],count:1,size:[0.03,0.3],hardness:[0.65,1],force:[0.2,0.6],tail:[0.45,0.9],spin:[0.3,0.8]}},
        {name:'Wood on Concrete',id:'cartoon_bounce',values:{material:1,surface:0,duration:[0.4,1.1],count:1,size:[0.25,0.65],hardness:[0.45,0.8],force:[0.4,0.85],tail:[0.15,0.5]}},
        {name:'Stone into Earth',id:'heavy_tumble',values:{material:4,surface:4,duration:[0.5,1.5],count:1,size:[0.75,1],hardness:[0.35,0.75],force:[0.55,1],tail:[0.2,0.6],spin:[0.25,0.8]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        const oldKeys=['masterVolume','seed','material','duration','count','bounce','gravity','size','hardness','spin'];
        if(params && oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key))) {
            for(const key of ['surface','force','tail'])if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,this.param_default(key),checkLocked);
        }
        super.apply_params(params,checkLocked);
    }
    set_param(name,value,checkLocked=false){if(name==='count'&&Number.isFinite(value))value=Math.round(value);super.set_param(name,value,checkLocked);}
}

// js/synths/Breathr.js
class Breathr extends PresetSynth {
    name='Breathr';
    canvas_bg_logo = 'img/logo_breathr.png';
    tooltip='Breathing, exertion and air moving through impossible lungs.';
    static DSP=Breathr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'source',display_name:'Airway',tooltip:'Airflow texture and airway motion.',default_value:0,columns:3,
            values:[['Airflow','Directional turbulent air through a changing mouth and throat.',0],['Retro','Stepped breath envelopes and coarse game noise.',1],['Snore','An obstructed airway fluttering under pressure.',2]]},
        {type:'BUTTONSELECT',name:'mode',display_name:'Breath',tooltip:'One intake or release, or a complete breathing cycle.',default_value:0,columns:2,
            values:[['Single','One breath; Direction blends its inward and outward character.',0],['Cycle','Inhale, hold and exhale, with optional repeated breaths.',1]]},
        ['Duration','Length of the breath or complete sequence, in seconds.','duration',0.65,0.15,5],
        ['Direction','From bright inward air (−1) to a soft outward release (+1).','direction',1,-1,1],
        ['Breaths','Number of inhale and exhale cycles.','cycles',1,1,10],
        ['Exertion','Force and turbulence of the airflow.','effort',0.55,0,1],
        ['Inhale Share','Portion of moving air spent inhaling.','inhale',0.42,0.1,0.9],
        ['Hold','Pause between inhaling and exhaling.','hold',0.04,0,0.7],
        ['Throat Size','From narrow high airways to a deep chest.','throat',0.5,0,1],
        ['Rasp','Airway roughness; in Snore mode, vibrating soft tissue.','rasp',0.1,0,1],
        ['Tremble','Uneven, shivering airflow.','flutter',0.15,0,1],
        ['Enclosure','Short reflections around a mask, helmet or cave.','space',0.1,0,1]
    ];
    recipes=[
        {name:'Inhale',id:'inhale',tip:'One short intake of air.',values:{mode:0,source:0,direction:[-1,-0.7],duration:[0.3,0.8],effort:[0.25,0.65],throat:[0.25,0.65],rasp:[0,0.16],flutter:[0.03,0.2],space:[0,0.12]}},
        {name:'Exhale',id:'exhale',tip:'One soft outward breath.',values:{mode:0,source:0,direction:[0.7,1],duration:[0.35,0.95],effort:[0.2,0.6],throat:[0.35,0.75],rasp:[0,0.15],flutter:[0.02,0.18],space:[0,0.12]}},
        {name:'Sigh',id:'sigh',tip:'A weary, gently fading release.',values:{mode:0,source:0,direction:[0.8,1],duration:[0.65,1.6],effort:[0.25,0.5],throat:[0.45,0.8],rasp:[0.08,0.3],flutter:[0.12,0.4],space:[0,0.15]}},
        {name:'Snore',id:'snore',tip:'One short rattling intake through a sleepy airway.',values:{mode:0,source:2,direction:[-1,-0.55],duration:[0.55,1.3],cycles:1,effort:[0.18,0.48],inhale:[0.45,0.65],hold:[0.08,0.22],throat:[0.4,0.78],rasp:[0.55,0.95],flutter:[0.28,0.65],space:[0,0.16]}},
        {name:'Tired Runner',id:'tired_runner',tip:'Fast, uneven breaths after a sprint.',values:{mode:1,source:[0,1],duration:[1.5,2.8],cycles:[3,6],effort:[0.65,1],inhale:[0.3,0.46],hold:[0,0.08],throat:[0.25,0.55],rasp:[0.2,0.5],flutter:[0.25,0.6],space:[0,0.12]}},
        {name:'Deep Breath',id:'deep_breath',tip:'One full, deliberate breath.',values:{mode:1,source:0,duration:[2.5,4.8],cycles:1,effort:[0.2,0.5],inhale:[0.42,0.58],hold:[0.02,0.12],throat:[0.4,0.75],rasp:[0,0.12],flutter:[0,0.1],space:[0,0.1]}},
        {name:'Held Breath',id:'held_breath',tip:'Air drawn in, held, then slowly released.',values:{mode:1,source:0,duration:[2.4,4.8],cycles:1,effort:[0.2,0.45],inhale:[0.23,0.45],hold:[0.42,0.68],throat:[0.25,0.6],rasp:[0.05,0.2],flutter:[0.05,0.3],space:[0,0.08]}},
        {name:'Gasp',id:'gasp',tip:'A single sharp, shaky intake.',values:{mode:0,source:[0,1],direction:[-1,-0.8],duration:[0.15,0.4],cycles:1,effort:[0.8,1],inhale:[0.16,0.3],hold:[0.1,0.28],throat:[0.04,0.3],rasp:[0.25,0.6],flutter:[0.25,0.65],space:[0,0.18]}},
        {name:'Sleeping Beast',id:'sleeping_beast',tip:'Huge sleepy lungs with a rough throat.',values:{mode:1,source:2,duration:[2.8,4.9],cycles:[1,2],effort:[0.2,0.5],inhale:[0.3,0.43],hold:[0.06,0.2],throat:[0.8,1],rasp:[0.65,1],flutter:[0.1,0.4],space:[0.15,0.4]}},
        {name:'Diver',id:'diver',tip:'Measured breathing through a resonant regulator.',values:{mode:1,source:[0,1],duration:[1.5,3.3],cycles:[2,3],effort:[0.55,0.85],inhale:[0.35,0.5],hold:[0.08,0.2],throat:[0.15,0.4],rasp:[0,0.12],flutter:[0.05,0.2],space:[0.4,0.7]}},
        {name:'Helmet',id:'helmet',tip:'Close, enclosed respirator airflow.',values:{mode:1,source:[0,1],duration:[1.5,3.5],cycles:[2,4],effort:[0.4,0.75],inhale:[0.36,0.5],hold:[0.06,0.18],throat:[0.45,0.75],rasp:[0.25,0.55],flutter:[0.03,0.16],space:[0.65,1]}},
        {name:'Ghost Breath',id:'ghost_breath',tip:'A cold, trembling exhalation in a hollow space.',values:{mode:1,source:[1,2],duration:[2.2,4.5],cycles:[1,2],effort:[0.12,0.4],inhale:[0.1,0.25],hold:[0.02,0.12],throat:[0.6,0.9],rasp:[0.4,0.8],flutter:[0.6,1],space:[0.55,0.95]}}
    ];
    constructor(){super();this.initialize_presets();}
    param_is_hidden(name){
        return this.params.mode===0?['cycles','inhale','hold'].includes(name):name==='direction';
    }
    create_random_template(){
        const singles=this.recipes.filter(recipe=>recipe.values.mode===0);
        const recipe=singles[Math.floor(Math.random()*singles.length)];
        this.generate_recipe(recipe.id);
        return [recipe.name.replace(/[^a-zA-Z0-9]/g,''),this.params];
    }
    apply_params(params,checkLocked=false){
        if(!params||typeof params!=='object')return;
        const defaults=this.default_params();
        const complete=['duration','cycles','effort','inhale','hold','throat','rasp','flutter','space','seed','masterVolume'].every(key=>Object.prototype.hasOwnProperty.call(params,key));
        super.apply_params(params,checkLocked);
        // Complete old saves predate the selector; partial edits retain the current choice.
        if(complete){
            if(!Object.prototype.hasOwnProperty.call(params,'source'))this.set_param('source',defaults.source,checkLocked);
            if(!Object.prototype.hasOwnProperty.call(params,'mode'))this.set_param('mode',1,checkLocked);
            if(!Object.prototype.hasOwnProperty.call(params,'direction'))this.set_param('direction',defaults.direction,checkLocked);
        }
    }
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='cycles'&&!(checkLocked&&this.locked_params[name]))this.params.cycles=Math.round(this.params.cycles);}
}

// js/synths/Choirr.js
class Choirr extends PresetSynth {
    name='Choirr';
    canvas_bg_logo = 'img/logo_choirr.png';
    tooltip='Sustained vowel ensembles, spectral choirs and wordless chords.';
    static DSP=Choirr_DSP;
    param_info=[PresetSynth.common_params[0],
        ['Ensemble Seed','Changes each singer’s tuning, vocal colour, vibrato timing, entrance and breath noise. Keeps the chord and root pitch.','seed',0.5,0,1],
        {type:'BUTTONSELECT',name:'harmony',display_name:'Harmony',tooltip:'Notes shared across the singers.',default_value:1,columns:3,values:[['Unison','Every singer holds the same note.',0],['Major','A bright major chord.',1],['Minor','A dark minor chord.',2],['Fifths','Open fifths and octaves.',3],['Cluster','Close and dissonant intervals.',4]]},
        ['Duration','Complete ensemble swell, in seconds.','duration',2.5,0.15,5],
        ['Pitch','Root note of the ensemble.','pitch',0.5,0,1],
        ['Singers','Independent vocal sources.','voices',6,1,12],
        ['Vowel','Morphs from oo through ah to ee.','vowel',0.35,0,1],
        ['Detune','Spread individual singers around their notes.','detune',0.4,0,1],
        ['Swell','Rounded attack and release of the held chord.','swell',0.5,0,1],
        ['Breath','Air mixed into every voice.','breath',0.1,0,1],
        ['Living Motion','Independent vibrato and gently shifting levels.','motion',0.4,0,1]
    ];
    recipes=[
        {name:'Angelic',id:'angelic',tip:'A bright, gently breathing major chorus.',values:{harmony:1,duration:[2.5,4.5],pitch:[0.45,0.66],voices:[6,10],vowel:[0.18,0.4],detune:[0.18,0.4],swell:[0.45,0.75],breath:[0.06,0.2],motion:[0.2,0.5]}},
        {name:'Ominous',id:'ominous',tip:'A low minor chord behind the door.',values:{harmony:2,duration:[2.6,4.8],pitch:[0.06,0.27],voices:[5,9],vowel:[0.08,0.32],detune:[0.35,0.7],swell:[0.25,0.6],breath:[0.08,0.24],motion:[0.15,0.45]}},
        {name:'Monks',id:'monks',tip:'Low voices holding an open fifth.',values:{harmony:3,duration:[2,4.5],pitch:[0.12,0.31],voices:[3,7],vowel:[0.28,0.55],detune:[0.1,0.3],swell:[0.1,0.35],breath:[0.01,0.12],motion:[0.08,0.25]}},
        {name:'Fairy Choir',id:'fairy_choir',tip:'Small, high singers in a shimmering chord.',values:{harmony:1,duration:[1.2,2.7],pitch:[0.66,0.9],voices:[5,10],vowel:[0.55,0.87],detune:[0.35,0.7],swell:[0.3,0.65],breath:[0.06,0.2],motion:[0.55,0.9]}},
        {name:'Robot Choir',id:'robot_choir',tip:'Steady synthetic vowel generators in unison.',values:{harmony:0,duration:[0.8,2.3],pitch:[0.32,0.62],voices:[3,8],vowel:[0.4,0.95],detune:[0,0.08],swell:[0.02,0.15],breath:[0,0.025],motion:[0,0.05]}},
        {name:'Ghost Chord',id:'ghost_chord',tip:'An airy minor chorus that fades into view.',values:{harmony:2,duration:[2.4,4.8],pitch:[0.34,0.57],voices:[7,12],vowel:[0.04,0.22],detune:[0.5,0.9],swell:[0.6,1],breath:[0.4,0.75],motion:[0.4,0.8]}},
        {name:'Victory Chord',id:'victory_chord',tip:'A full, open ah announcing success.',values:{harmony:1,duration:[0.8,2],pitch:[0.35,0.57],voices:[8,12],vowel:[0.4,0.58],detune:[0.12,0.32],swell:[0.15,0.4],breath:[0.02,0.1],motion:[0.15,0.4]}},
        {name:'Void Voices',id:'void_voices',tip:'An unsettled cluster of low, wordless voices.',values:{harmony:4,duration:[2.4,4.9],pitch:[0.03,0.25],voices:[6,12],vowel:[0.45,0.8],detune:[0.65,1],swell:[0.3,0.7],breath:[0.15,0.5],motion:[0.6,1]}}
    ];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='voices'&&!(checkLocked&&this.locked_params[name]))this.params.voices=Math.round(this.params.voices);}
}

// js/synths/Pluckr.js
class Pluckr extends PresetSynth {
    name='Pluckr';
    canvas_bg_logo = 'img/logo_pluckr.png';
    tooltip='Plucked strings, sympathetic bridges and small magical instruments.';
    static DSP=Pluckr_DSP;
    param_info=[...PresetSynth.common_params,
        {type:'BUTTONSELECT',name:'material',display_name:'String',tooltip:'String material changes the excitation, loss and wave dispersion.',default_value:0,columns:3,
            values:[['Nylon','A smooth, flexible string with a rounded ring.',0],['Steel','Bright wire with stiff, persistent upper partials.',1],['Gut','A soft fibre string with warm, uneven loss.',2],
                ['Rubber','A thick elastic string that rapidly absorbs vibration.',3],['Glass','An impossible rigid filament with dispersing partials.',4]]},
        ['Duration','Total string ring, in seconds.','duration',1.8,0.15,5],
        ['Pitch','Root string tuning.','pitch',0.5,0,1],
        ['Strings','Strings in the open chord.','strings',3,1,8],
        ['Damping','How quickly vibration is absorbed.','damping',0.25,0,1],
        ['Brightness','Excitation and feedback-loop high frequencies.','brightness',0.6,0,1],
        ['Pluck Point','Where along the string the finger pulls.','pluck',0.3,0,1],
        ['Coupling','Energy exchanged through a common bridge.','coupling',0.15,0,1],
        ['Strum','Delay between successive string releases.','strum',0.2,0,1],
        ['Tremolo Volume','Depth of the pulsing string volume; does not change pitch.','tremolo',0,0,1],
        ['Vibrato Pitch','Depth of the gentle pitch wobble, up to about three quarters of a semitone.','vibrato',0,0,1],
        ['Motion Speed','Pulses per second for both tremolo and vibrato.','tremoloRate',4,0.2,12],
        ['Loose Tuning','Independent imperfections in string tuning.','inharmonic',0.05,0,1]
    ];
    recipes=[
        {name:'Harp',id:'harp',tip:'A clear open chord with a long ring.',values:{material:[0,2],duration:[2,4],pitch:[0.35,0.65],strings:[3,6],damping:[0.05,0.25],brightness:[0.25,0.55],pluck:[0.2,0.6],coupling:[0.1,0.35],strum:[0.3,0.65],inharmonic:[0.01,0.08]}},
        {name:'Kalimba',id:'kalimba',tip:'A small bright thumb-piano tine.',values:{material:[1,4],duration:[0.7,1.6],pitch:[0.5,0.8],strings:[1,2],damping:[0.25,0.5],brightness:[0.55,0.9],pluck:[0.1,0.4],coupling:[0.05,0.2],strum:[0.05,0.2],inharmonic:[0.02,0.14]}},
        {name:'Muted Guitar',id:'muted_guitar',tip:'A short palm-muted chord.',values:{material:[0,2,3],duration:[0.4,0.9],pitch:[0.2,0.48],strings:[3,6],damping:[0.7,0.94],brightness:[0.12,0.38],pluck:[0.25,0.65],coupling:[0.15,0.45],strum:[0.08,0.22],inharmonic:[0.03,0.15]}},
        {name:'Metal String',id:'metal_string',tip:'A hard, bright wire with a persistent ring.',values:{material:1,duration:[1.4,3.5],pitch:[0.3,0.7],strings:[1,3],damping:[0.02,0.18],brightness:[0.8,1],pluck:[0.02,0.2],coupling:[0.1,0.4],strum:[0.04,0.2],inharmonic:[0.1,0.3]}},
        {name:'Magic Harp',id:'magic_harp',tip:'A cascade of high sympathetic strings.',values:{material:4,duration:[2,4.5],pitch:[0.5,0.8],strings:[5,8],damping:[0.02,0.16],brightness:[0.35,0.65],pluck:[0.2,0.65],coupling:[0.6,1],strum:[0.65,1],inharmonic:[0.1,0.3]}},
        {name:'Bass Pluck',id:'bass_pluck',tip:'One thick string with a round body.',values:{material:[0,2,3],duration:[0.8,2.4],pitch:[0.02,0.2],strings:1,damping:[0.15,0.4],brightness:[0.08,0.3],pluck:[0.3,0.6],coupling:[0.05,0.25],strum:0,inharmonic:[0.01,0.12]}},
        {name:'Broken String',id:'broken_string',tip:'A loose, mismatched chord dying unevenly.',values:{material:[2,3],duration:[0.6,1.5],pitch:[0.12,0.5],strings:[2,5],damping:[0.45,0.8],brightness:[0.5,0.95],pluck:[0.02,0.9],coupling:[0.4,0.9],strum:[0.2,0.7],inharmonic:[0.8,1]}},
        {name:'Quest Pluck',id:'quest_pluck',tip:'A compact upward chord for a discovered clue.',values:{material:[0,1,4],duration:[0.8,1.8],pitch:[0.45,0.7],strings:[3,5],damping:[0.15,0.35],brightness:[0.45,0.8],pluck:[0.2,0.55],coupling:[0.2,0.5],strum:[0.4,0.7],inharmonic:[0.02,0.12]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        if(!params||typeof params!=='object')return;
        const defaults=this.default_params();
        const complete=['duration','pitch','strings','damping','brightness','pluck','coupling','strum','inharmonic','seed','masterVolume'].every(key=>Object.prototype.hasOwnProperty.call(params,key));
        if(complete)for(const key of ['material','tremolo','tremoloRate','vibrato']) {
            if(!Object.prototype.hasOwnProperty.call(params,key))this.set_param(key,defaults[key],checkLocked);
        }
        // Retired Gravity snapshots become glass strings with explicit modulation.
        const migrated=params.material===5 ? {...params,material:4,tremolo:params.tremolo??0.35,tremoloRate:params.tremoloRate??1.7} : params;
        super.apply_params(migrated,checkLocked);
    }

    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='strings'&&!(checkLocked&&this.locked_params[name]))this.params.strings=Math.round(this.params.strings);}
}

// js/synths/Glitchr.js
class Glitchr extends PresetSynth {
    name='Glitchr';
    canvas_bg_logo = 'img/logo_glitchr.png';
    tooltip='Lost buffers, codec warble, tape scrubbing and torn digital audio.';
    static DSP=Glitchr_DSP;
    param_info=[...PresetSynth.common_params,
        ['Duration','Length in seconds.','duration',0.7,0.08,4],
        ['Pitch','Pitch of the captured sound or data carrier.','pitch',0.5,0,1],
        ['Fragment','Length of the damaged buffer, packet or grain.','fragment',0.3,0,1],
        ['Repeat','Hold the same captured fragment before taking fresh audio.','repeat',0.4,0,1],
        ['Chaos','Read-head jumps, packet damage and unstable playback speed.','chaos',0.5,0,1],
        ['Dropout','Lose complete packets of audio.','dropout',0.2,0,1],
        ['Crush','Quantize amplitude with fewer usable bits.','crush',0.3,0,1],
        ['Sample Hold','Lower the damaged output sample rate.','rate',0.3,0,1],
        {type:'BUTTONSELECT',name:'mode',display_name:'Failure',tooltip:'Each failure uses a different processing mechanism.',default_value:0,columns:2,header:true,values:[['Underrun','A stalled read buffer repeats, then jumps ahead.',0],['Codec Warble','Coarsely coded frequency bands flutter and smear.',1],['Tape Scrub','An unstable read head scrubs backward and forward.',2],['Bit Rot','Decimated samples lose resolution and flip bits.',3],['Data Squeal','Binary data leaks into the audio carrier.',4],['Granular Tear','Overlapping fragments scatter and reverse.',5],['Stutter','A captured phrase is retriggered in short bursts.',6],['Spectral Freeze','Captured partials hang and change in blocks.',7]]}
    ];
    recipes=[
        {name:'Buffer Underrun',id:'save_corruption',values:{mode:0,duration:[0.5,1.4],pitch:[0.25,0.65],fragment:[0.03,0.3],repeat:[0.6,0.95],chaos:[0.25,0.65],dropout:[0.2,0.55],crush:[0.1,0.4],rate:[0,0.2]}},
        {name:'Codec Warble',id:'teleport_error',values:{mode:1,duration:[0.7,1.7],pitch:[0.3,0.6],fragment:[0.1,0.45],repeat:[0.3,0.7],chaos:[0.5,1],dropout:[0.05,0.3],crush:[0.4,0.8],rate:[0,0.2]}},
        {name:'Bit Rot',id:'bit_rot',values:{mode:3,duration:[0.6,1.6],pitch:[0.15,0.5],fragment:[0.15,0.6],repeat:[0.15,0.6],chaos:[0.2,0.7],dropout:[0.1,0.45],crush:[0.65,1],rate:[0.55,1]}},
        {name:'Phrase Stutter',id:'buffer_skip',values:{mode:6,duration:[0.4,1.2],pitch:[0.35,0.7],fragment:[0.1,0.5],repeat:[0.75,1],chaos:[0.05,0.4],dropout:[0.05,0.3],crush:[0,0.35],rate:[0,0.2]}},
        {name:'Data Squeal',id:'corrupt_pickup',values:{mode:4,duration:[0.2,0.8],pitch:[0.4,0.85],fragment:[0.05,0.4],repeat:[0.25,0.7],chaos:[0.45,0.95],dropout:[0.05,0.3],crush:[0.25,0.7],rate:[0,0.2]}},
        {name:'Spectral Freeze',id:'broken_terminal',values:{mode:7,duration:[0.8,2.2],pitch:[0.25,0.65],fragment:[0.3,0.85],repeat:[0.5,0.9],chaos:[0.3,0.8],dropout:[0.05,0.3],crush:[0.1,0.5],rate:[0,0.15]}},
        {name:'Tape Scrub',id:'rewind_burst',values:{mode:2,duration:[0.5,1.5],pitch:[0.3,0.65],fragment:[0.05,0.6],repeat:[0.25,0.75],chaos:[0.4,1],dropout:[0,0.15],crush:[0,0.2],rate:[0,0.1]}},
        {name:'Granular Tear',id:'digital_death',values:{mode:5,duration:[0.6,1.8],pitch:[0.2,0.65],fragment:[0.08,0.55],repeat:[0.2,0.7],chaos:[0.65,1],dropout:[0.05,0.3],crush:[0.2,0.6],rate:[0.05,0.35]}}
    ];
    constructor(){super();this.initialize_presets();}
    apply_params(params,checkLocked=false){
        const oldKeys=['masterVolume','seed','duration','pitch','fragment','repeat','chaos','dropout','crush','rate'];
        if(params && oldKeys.every(key=>Object.prototype.hasOwnProperty.call(params,key)) && !Object.prototype.hasOwnProperty.call(params,'mode'))this.set_param('mode',this.param_default('mode'),checkLocked);
        super.apply_params(params,checkLocked);
    }
}

const puredata_functions = {
"dirt": function anonymous(envelope_signal
) {
const s_32 = pd_noise();
const s_31 = pd_lop(s_32,pd_c(80));
const s_30 = pd_mul(s_31,pd_c(70));
const s_29 = envelope_signal;
const s_28 = pd_add(s_29,pd_c(0.3));
const s_27 = pd_mul(s_28,s_30);
const s_26 = pd_mul(s_27,pd_c(70));
const s_25 = pd_add(s_26,pd_c(70));
const s_24 = pd_osc(s_25);
const s_23 = pd_hip(s_24,pd_c(200));
const s_22 = pd_clip(s_23,pd_c(-1),pd_c(1));
const s_21 = pd_mul(s_22,pd_c(0.04));
const s_18 = pd_mul(s_29,s_29);
const s_14 = pd_mul(s_18,s_18);
const s_6 = pd_mul(s_14,pd_c(500));
const s_5 = pd_add(s_6,pd_c(40));
const s_4 = pd_osc(s_5);
const s_3 = pd_mul(s_4,s_14);
const s_2 = pd_mul(s_3,pd_c(0.5));
const s_1 = pd_add(s_2,s_21);
const s_0 = s_1;
return s_0;

},
"grass": function anonymous(envelope_signal
) {
const s_60 = pd_noise();
const s_59 = pd_lop(s_60,pd_c(16));
const s_58 = pd_mul(s_59,pd_c(23800));
const s_57 = pd_add(s_58,pd_c(3400));
const s_56 = pd_clip(s_57,pd_c(2000),pd_c(10000));
const s_54 = pd_lop(s_60,pd_c(2000));
const s_52 = pd_lop(s_60,pd_c(300));
const s_51 = pd_div(s_52,s_54);
const s_50 = pd_hip(s_51,pd_c(2500));
const s_43 = pd_mul(s_50,s_50);
const s_29 = pd_mul(s_43,s_43);
const s_28 = pd_mul(s_29,pd_c(1e-05));
const s_27 = pd_clip(s_28,pd_c(-0.9),pd_c(0.9));
const s_26 = pd_vcf(s_27,s_56,pd_c(1));
const s_25 = pd_hip(s_26,pd_c(900));
const s_24 = pd_mul(s_25,pd_c(0.3));
const s_23 = envelope_signal;
const s_22 = pd_mul(s_23,s_24);
const s_19 = pd_mul(s_23,s_23);
const s_15 = pd_mul(s_19,s_19);
const s_7 = pd_mul(s_15,pd_c(600));
const s_6 = pd_add(s_7,pd_c(30));
const s_5 = pd_osc(s_6);
const s_4 = pd_clip(s_5,pd_c(0),pd_c(0.5));
const s_3 = pd_mul(s_4,s_15);
const s_2 = pd_mul(s_3,pd_c(0.8));
const s_1 = pd_add(s_2,s_22);
const s_0 = s_1;
return s_0;

},
"gravel": function anonymous(envelope_signal
) {
const s_27 = envelope_signal;
const s_26 = pd_mul(s_27,pd_c(1000));
const s_25 = pd_noise();
const s_24 = pd_lop(s_25,pd_c(50));
const s_23 = pd_mul(s_24,pd_c(50000));
const s_22 = pd_add(s_23,s_26);
const s_21 = pd_clip(s_22,pd_c(500),pd_c(10000));
const s_19 = pd_lop(s_25,pd_c(2000));
const s_17 = pd_lop(s_25,pd_c(300));
const s_16 = pd_div(s_17,s_19);
const s_15 = pd_hip(s_16,pd_c(400));
const s_8 = pd_mul(s_15,s_15);
const s_7 = pd_mul(s_8,pd_c(0.01));
const s_6 = pd_clip(s_7,pd_c(-0.9),pd_c(0.9));
const s_5 = pd_vcf(s_6,s_21,pd_c(3));
const s_4 = pd_hip(s_5,pd_c(200));
const s_3 = pd_mul(s_4,pd_c(2));
const s_1 = pd_mul(s_27,s_3);
const s_0 = s_1;
return s_0;

},
"snow": function anonymous(envelope_signal
) {
const s_29 = envelope_signal;
const s_27 = pd_mul(s_29,pd_c(9000));
const s_26 = pd_add(s_27,pd_c(700));
const s_25 = pd_noise();
const s_24 = pd_lop(s_25,pd_c(10));
const s_23 = pd_mul(s_24,pd_c(17));
const s_19 = pd_mul(s_23,s_23);
const s_18 = pd_add(s_19,pd_c(0.5));
const s_16 = pd_lop(s_25,pd_c(70));
const s_14 = pd_lop(s_25,pd_c(50));
const s_13 = pd_div(s_14,s_16);
const s_12 = pd_noise();
const s_11 = pd_lop(s_12,pd_c(900));
const s_9 = pd_lop(s_12,pd_c(110));
const s_8 = pd_div(s_9,s_11);
const s_7 = pd_mul(s_8,s_13);
const s_6 = pd_mul(s_7,s_18);
const s_5 = pd_clip(s_6,pd_c(-1),pd_c(1));
const s_4 = pd_hip(s_5,pd_c(300));
const s_3 = pd_vcf(s_4,s_26,pd_c(0.5));
const s_2 = pd_mul(s_3,s_29);
const s_1 = pd_mul(s_2,pd_c(0.2));
const s_0 = s_1;
return s_0;

},
"wood": function anonymous(envelope_signal
) {
const s_29 = pd_noise();
const s_28 = pd_bp(s_29,pd_c(201),pd_c(70));
const s_26 = pd_bp(s_29,pd_c(189),pd_c(90));
const s_24 = pd_bp(s_29,pd_c(156),pd_c(90));
const s_22 = pd_bp(s_29,pd_c(123),pd_c(20));
const s_21 = pd_mul(pd_polyadd(s_22,s_24,s_26,s_28),pd_c(8));
const s_20 = envelope_signal;
const s_18 = pd_mul(s_20,s_20);
const s_17 = pd_mul(s_18,pd_c(2));
const s_16 = pd_mul(s_17,s_21);
const s_15 = pd_mul(s_16,pd_c(0.6));
const s_14 = pd_noise();
const s_13 = pd_bp(s_14,pd_c(154),pd_c(90));
const s_11 = pd_bp(s_14,pd_c(139),pd_c(90));
const s_9 = pd_bp(s_14,pd_c(134),pd_c(90));
const s_7 = pd_bp(s_14,pd_c(95),pd_c(90));
const s_6 = pd_mul(pd_polyadd(s_7,s_9,s_11,s_13),pd_c(6));
const s_4 = pd_sqrt(s_20);
const s_3 = pd_mul(s_4,s_6);
const s_2 = pd_mul(s_3,pd_c(0.5));
const s_1 = pd_add(s_2,s_15);
const s_0 = s_1;
return s_0;

}
};
const BFXR_SYNTHS = {Bfxr,Footsteppr,Transfxr,Clonkr,Machinr,Jinglr,Squishr,Mixr,Crittr,Birdr,Signlr,Fractr,Riftr,Swarmr,Rustlr,Boomr,Zappr,Whooshr,Bouncr,Breathr,Choirr,Pluckr,Glitchr};
// Portable data, existing preset generators and PCM synthesis; no playback or DOM.
const LibrarySounds = {
    engine(name) {
        if (!Object.prototype.hasOwnProperty.call(BFXR_SYNTHS, name)) {
            throw new Error('Unknown synth: ' + name);
        }
        return new BFXR_SYNTHS[name]();
    },

    seed(value) {
        if (value === undefined) return global.Math.random();
        if (typeof value !== 'string' && (typeof value !== 'number' || !Number.isFinite(value))) {
            throw new TypeError('A preset seed must be a finite number or string');
        }
        let hash = 2166136261;
        const text = typeof value + ':' + value;
        for (let i = 0; i < text.length; i++) hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
        return (hash >>> 0) / 4294967296;
    },

    seeded(seed, action) {
        const previous = Math.random;
        Math.random = SoundDSP.rng(seed);
        try { return action(); } finally { Math.random = previous; }
    },

    categories(synth) {
        if (synth.name === 'Footsteppr') return Footsteppr_DSP.terrains.map(id => [id, id]);
        return synth.templates.filter(template => template[2].startsWith('generate_'))
            .map(template => [template[2].replace(/^generate_(?:family_)?/, ''), template[2]]);
    },

    preset(name, id, seed) {
        const synth = this.engine(name);
        const category = this.categories(synth).find(entry => entry[0] === id);
        if (!category) throw new Error('Unknown preset for ' + name + ': ' + id);
        const renderSeed = this.seed(seed);
        this.seeded(renderSeed, () => {
            if (name === 'Footsteppr') {
                synth.randomize_params();
                synth.set_param('terrain', Footsteppr_DSP.terrains.indexOf(id));
            } else synth[category[1]]();
        });
        return {synth_type: name, version: synth.version, params: JSON.parse(JSON.stringify(synth.params)), renderSeed};
    },

    normalize(input) {
        if (typeof input === 'string') {
            try { input = JSON.parse(input); } catch { throw new TypeError('Invalid sound JSON'); }
        }
        if (!input || typeof input !== 'object' || !input.params ||
            typeof input.params !== 'object' || Array.isArray(input.params)) {
            throw new TypeError('A sound needs synth_type and a params object');
        }
        const synth = this.engine(input.synth_type);
        const renderSeed = input.renderSeed === undefined ? 0.5 : input.renderSeed;
        if (!Number.isFinite(renderSeed) || renderSeed < 0 || renderSeed > 1) {
            throw new TypeError('renderSeed must be a number between 0 and 1');
        }
        const params = Mixr.sanitize_source(synth, JSON.parse(JSON.stringify(input.params)));
        return {synth_type: synth.name, version: synth.version, params, renderSeed};
    },

    render(sound) {
        const synth = this.engine(sound.synth_type);
        synth.apply_params(sound.params);
        return this.seeded(sound.renderSeed, () => synth.render());
    },

    mutate(sound, amount, seed) {
        if (amount === 0) return sound;
        return this.seeded(seed, () => {
            const synth = this.engine(sound.synth_type);
            synth.apply_params(sound.params);
            // Melody control setters normally regenerate notes; preserve the saved score here.
            const batching = synth.batching;
            if ('batching' in synth) synth.batching = true;
            for (const row of synth.param_info) {
                const info = synth.get_param_normalized(row);
                if (['masterVolume', 'seed', 'instrumentSeed'].includes(info.name) ||
                    !['RANGE', 'KNOB_TRANSITION'].includes(info.type) || Math.random() < .5) continue;
                const offset = () => (Math.random() * 2 - 1) * amount * (info.max_value - info.min_value);
                const value = synth.params[info.name];
                synth.set_param(info.name, info.type === 'KNOB_TRANSITION'
                    ? {...value, start: value.start + offset(), end: value.end + offset()}
                    : value + offset());
            }
            if ('batching' in synth) synth.batching = batching;
            if (synth.name === 'Mixr') {
                synth.set_param('sources', synth.get_sources().map(source => source && ({...source,
                    params: this.mutate({synth_type: source.synth, params: source.params,
                        renderSeed: source.renderSeed ?? sound.renderSeed}, amount, Math.random()).params})));
            }
            return {...sound, params: JSON.parse(JSON.stringify(synth.params))};
        });
    }
};

// Sample buffers and mutation definitions have separate bounded LRU budgets.
class LibraryLRU {
    constructor(budget, limit = Infinity) {
        this.budget = budget;
        this.limit = limit;
        this.bytes = 0;
        this.entries = new Map();
    }

    get(key) {
        const entry = this.entries.get(key);
        if (!entry) return undefined;
        this.entries.delete(key);
        this.entries.set(key, entry);
        return entry.value;
    }

    set(key, value, bytes) {
        const previous = this.entries.get(key);
        if (previous) { this.bytes -= previous.bytes; this.entries.delete(key); }
        if (bytes > this.budget) return value;
        while (this.bytes + bytes > this.budget || this.entries.size >= this.limit) {
            const oldest = this.entries.keys().next().value;
            this.bytes -= this.entries.get(oldest).bytes;
            this.entries.delete(oldest);
        }
        this.entries.set(key, {value, bytes});
        this.bytes += bytes;
        return value;
    }

    clear() { this.entries.clear(); this.bytes = 0; }
}

const LibraryCache = {
    samples: new LibraryLRU(32 * 1024 * 1024),
    pools: new LibraryLRU(4 * 1024 * 1024, 256),
    generation: 0,

    stable(value) {
        if (!value || typeof value !== 'object') return JSON.stringify(value);
        if (Array.isArray(value)) return '[' + value.map(v => this.stable(v)).join(',') + ']';
        return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + this.stable(value[key])).join(',') + '}';
    },

    key(sound) {
        return this.stable({synth: sound.synth_type, params: sound.params, renderSeed: sound.renderSeed});
    },

    remember(key, entry) {
        // AudioBuffer and PCM each own a sample allocation; account for both.
        return this.samples.set(key, entry, entry.pcm.byteLength * (entry.buffer ? 2 : 1) + key.length * 2);
    },

    sound(sound) {
        const key = this.key(sound);
        return this.samples.get(key) || this.remember(key, {pcm: LibrarySounds.render(sound), buffer: null});
    },

    pool(sound, amount, count) {
        if (!Number.isFinite(amount) || amount < 0 || amount > 1) {
            throw new RangeError('Mutation amount must be between 0 and 1');
        }
        if (!Number.isInteger(count) || count < 1 || count > 256) {
            throw new RangeError('Mutation count must be an integer between 1 and 256');
        }
        const key = this.key(sound) + ':' + amount + ':' + count;
        let pool = this.pools.get(key);
        if (!pool) {
            pool = {key, original: sound, amount, count, sounds: [], next: 0};
            this.rememberPool(pool);
        }
        return pool;
    },

    rememberPool(pool) {
        const bytes = (pool.key.length + JSON.stringify(pool.original).length +
            JSON.stringify(pool.sounds).length) * 2;
        this.pools.set(pool.key, pool, bytes);
    },

    variation(pool, index) {
        if (!pool.sounds[index]) {
            pool.sounds[index] = LibrarySounds.mutate(pool.original, pool.amount,
                LibrarySounds.seed(pool.key + ':' + index));
            this.rememberPool(pool);
        }
        return pool.sounds[index];
    },

    mutated(sound, amount, count) {
        const pool = this.pool(sound, amount, count);
        const index = pool.next < count ? pool.next++ : Math.floor(global.Math.random() * count);
        return this.variation(pool, index);
    },

    yield() { return new Promise(resolve => global.setTimeout(resolve, 0)); },

    async warm(sound) {
        const generation = this.generation;
        await this.yield();
        if (generation === this.generation) this.sound(sound);
    },

    async warmMutations(sound, amount, count) {
        const pool = this.pool(sound, amount, count), generation = this.generation;
        for (let index = 0; index < count; index++) {
            await this.yield();
            if (generation !== this.generation) return;
            this.sound(this.variation(pool, index));
        }
        pool.next = count;
    },

    clear() { this.generation++; this.samples.clear(); this.pools.clear(); }
};

// Lazy Web Audio setup and one independent source/gain pair per play.
const LibraryPlayback = {
    context: null,
    voices: new Set(),
    unlocking: false,
    listening: false,

    options(options = {}) {
        if (!options || typeof options !== 'object') throw new TypeError('Playback options must be an object');
        const volume = options.volume ?? 1, pitch = options.pitch ?? 0, loop = options.loop ?? false;
        if (!Number.isFinite(volume) || volume < 0) throw new RangeError('volume must be a finite nonnegative number');
        if (!Number.isFinite(pitch) || pitch < -96 || pitch > 96) throw new RangeError('pitch must be between -96 and 96 semitones');
        if (typeof loop !== 'boolean') throw new TypeError('loop must be a boolean');
        return {volume, pitch, loop};
    },

    audio() {
        if (!this.context || this.context.state === 'closed') {
            const Constructor = global.AudioContext || global.webkitAudioContext;
            if (!Constructor) throw new Error('This browser does not support Web Audio');
            this.context = new Constructor();
        }
        this.unlock();
        return this.context;
    },

    unlock() {
        if (!this.context || this.context.state === 'running' || this.unlocking) return;
        this.unlocking = true;
        // Attach immediately: some browsers leave resume() pending until a gesture.
        this.listen();
        Promise.resolve(this.context.resume()).then(() => {
            this.unlocking = false;
            if (this.context.state === 'running') this.unlisten();
        }, () => { this.unlocking = false; });
    },

    gesture() {
        // Retry even if an earlier autoplay-blocked resume remains pending.
        LibraryPlayback.unlocking = false;
        LibraryPlayback.unlock();
    },

    listen() {
        if (this.listening || !global.addEventListener) return;
        this.listening = true;
        for (const event of ['pointerdown', 'touchend', 'keydown']) {
            global.addEventListener(event, this.gesture, {capture: true, passive: true});
        }
    },

    unlisten() {
        if (!this.listening) return;
        this.listening = false;
        for (const event of ['pointerdown', 'touchend', 'keydown']) {
            global.removeEventListener(event, this.gesture, {capture: true});
        }
    },

    play(sound, options) {
        const settings = this.options(options);
        const context = this.audio(), key = LibraryCache.key(sound), entry = LibraryCache.sound(sound);
        if (!entry.buffer) {
            entry.buffer = context.createBuffer(1, entry.pcm.length, SAMPLE_RATE);
            entry.buffer.copyToChannel(entry.pcm, 0);
            LibraryCache.remember(key, entry);
        }
        const source = context.createBufferSource(), gain = context.createGain();
        source.buffer = entry.buffer;
        source.loop = settings.loop;
        source.playbackRate.value = 2 ** (settings.pitch / 12);
        gain.gain.value = settings.volume;
        source.connect(gain); gain.connect(context.destination);
        let active = true;
        const cleanup = () => {
            if (!active) return;
            active = false;
            source.disconnect(); gain.disconnect();
            this.voices.delete(voice);
        };
        const voice = {stop() {
            if (!active) return;
            source.stop(); cleanup();
        }};
        source.onended = cleanup;
        this.voices.add(voice);
        try { source.start(context.currentTime); } catch (error) { cleanup(); throw error; }
        return voice;
    },

    stopAll() { for (const voice of this.voices) voice.stop(); }
};

// Only this object escapes the bundle's private closure.
global.bfxr = {
    version: '1.0.0',
    sampleRate: SAMPLE_RATE,
    synths: () => Object.keys(BFXR_SYNTHS),
    presets: name => LibrarySounds.categories(LibrarySounds.engine(name)).map(entry => entry[0]),
    preset: (name, id, seed) => LibrarySounds.preset(name, id, seed),
    render: sound => LibraryCache.sound(LibrarySounds.normalize(sound)).pcm.slice(),
    play: (sound, options) => LibraryPlayback.play(LibrarySounds.normalize(sound), options),
    playMutated: (sound, amount = .05, count = 15, options) => LibraryPlayback.play(
        LibraryCache.mutated(LibrarySounds.normalize(sound), amount, count), options),
    cache: sound => LibraryCache.warm(LibrarySounds.normalize(sound)),
    cacheMutations: (sound, amount = .05, count = 15) => LibraryCache.warmMutations(
        LibrarySounds.normalize(sound), amount, count),
    stopAll: () => LibraryPlayback.stopAll(),
    clearCache: () => LibraryCache.clear()
};

})(globalThis);
